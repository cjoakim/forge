import logging
import os
import re
import time
import traceback

import httpx

from src.io.fs import FS
from src.os.env import Env

# Determine the retail (list) price of the models returned by
# FoundryModels#list_available_models, using the public Azure Retail Prices API.
# See https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices
#
# The price meters do not use model IDs; they use abbreviated meter names such as
# "GPT 5 Inpt Glbl 1M Tokens" or "gpt 4.1 cached Inp regnl Tokens".  This class parses
# those names into (model key, token type, deployment type) and matches them to the models.
# Notes:
# - These are pay-as-you-go list prices, not EA/MCA negotiated rates.
# - Azure Marketplace models (e.g. Anthropic Claude) are not in the Retail Prices API.
# - Long-context, flex, and priority-processing meters are ignored; the standard price is reported.

RETAIL_PRICES_URL = "https://prices.azure.com/api/retail/prices"

CACHED_WORDS = {"cached", "cache", "cchd", "ccchd", "cd"}
INPUT_WORDS = {"inp", "inpt", "input", "in"}
OUTPUT_WORDS = {"outp", "outpt", "output", "opt", "out"}
GLOBAL_WORDS = {"glbl", "gl", "glb", "global"}
DATAZONE_WORDS = {"dz", "dzone", "dzn", "datazone"}
REGIONAL_WORDS = {"regnl", "rgnl", "regional"}

# Meters containing any of these words are not standard per-token inference prices.
SKIP_WORDS = {
    "ft",
    "finetuned",
    "training",
    "hosting",
    "grader",
    "grdr",
    "rft",
    "dev",
    "pp",
    "flex",
    "fl",
    "longco",
    "loco",
    "l",
    "aud",
    "audio",
    "rt",
    "rtime",
    "realtime",
    "tts",
    "transcribe",
    "trscb",
    "tcrb",
    "img",
    "image",
    "images",
    "provisioned",
}

# Words removed from both meter names and model names before comparing them.
IGNORE_WORDS = {
    "tokens",
    "1m",
    "std",
    "shortco",
    "shco",
    "gpt",
    "deepseek",
    "grok",
    "kimi",
    "mistral",
    "cohere",
    "instruct",
    "fp8",
    "128e",
    "16e",
    "thinking",
}

# Model names which can't be derived from their meter names; model name -> meter model key.
MODEL_KEY_ALIASES = {
    "grok-4-1-fast-non-reasoning": "4.1",
    "grok-4-1-fast-reasoning": "4.1",
    "grok-4-20-non-reasoning": "4.2",
    "grok-4-20-reasoning": "4.2",
    "deepseek-v3.2-speciale": "v3.2sp",
    "mistral-medium-3-5": "mm3.5",
    "phi-4-multimodal-instruct": "phi4minimm",
    "cohere-command-a-plus-05-2026": "commandaplus",
    "text-embedding-ada-002": "embeddingada",
    "deepseek-v4.1-flash": "fwdsv4.1flash",
}

# Retail price productName prefixes for each model format (publisher), so that e.g. the
# meters for gpt-4.1 and Grok 4.1 aren't confused.  Fireworks hosts models of several publishers.
FORMAT_PRODUCT_PREFIXES = {
    "OpenAI": ["Azure OpenAI"],
    "OpenAI-OSS": ["Azure OpenAI OSS"],
    "xAI": ["Azure Grok"],
    "DeepSeek": ["Azure Deepseek"],
    "MoonshotAI": ["Azure Kimi"],
    "Meta": ["Azure Llama"],
    "Mistral AI": ["Azure Mistral"],
    "Microsoft": ["Azure Phi", "MAI"],
    "Cohere": ["Cohere"],
    "Alibaba": ["Qwen"],
}
ANY_FORMAT_PRODUCT_PREFIXES = ["Azure Fireworks"]

SKU_NAMES = {
    ("global", False): "GlobalStandard",
    ("datazone", False): "DataZoneStandard",
    ("regional", False): "Standard",
    ("global", True): "GlobalBatch",
    ("datazone", True): "DataZoneBatch",
}

PTU_METER_SKUS = {
    "Provisioned Managed Global Unit": "GlobalProvisionedManaged",
    "Provisioned Managed Data Zone Unit": "DataZoneProvisionedManaged",
    "Provisioned Managed Regional Unit": "ProvisionedManaged",
}


class FoundryModelPricing:
    def __init__(self, region: str | None = None, opts={}):
        """
        Args:
            region: The Azure region (armRegionName) to price in.
                Default to AZURE_FOUNDRY_REGION environment variable, then eastus.
            opts: optional "cache_hours" (default 24) for the cached price list in tmp/.
        """
        self.region = region if region else Env.azure_foundry_region()
        self.opts = opts
        self.cache_file = f"tmp/azure_retail_prices_foundry_{self.region}.json"

    def get_retail_prices(self, refresh: bool = False) -> list[dict]:
        """
        Return the Foundry Models consumption price items for the region,
        from the local cache file if it is recent, else from the Retail Prices API.
        """
        try:
            cache_hours = float(self.opts.get("cache_hours", 24))
            if not refresh and os.path.exists(self.cache_file):
                age_hours = (time.time() - os.path.getmtime(self.cache_file)) / 3600.0
                if age_hours < cache_hours:
                    items = FS.read_json_list(self.cache_file)
                    if items:
                        logging.info(
                            f"ModelPricing#get_retail_prices using cache: {self.cache_file}"
                        )
                        return items

            odata_filter = " and ".join(
                [
                    "serviceName eq 'Foundry Models'",
                    f"armRegionName eq '{self.region}'",
                    "priceType eq 'Consumption'",
                ]
            )
            items, url, params = [], RETAIL_PRICES_URL, {"$filter": odata_filter}
            while url:
                resp = httpx.get(url, params=params, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                items.extend(data.get("Items", []))
                url, params = data.get("NextPageLink"), None
            logging.info(
                f"ModelPricing#get_retail_prices fetched {len(items)} items for {self.region}"
            )
            FS.write_json(items, self.cache_file, pretty=True, verbose=False)
            return items
        except Exception as e:
            logging.error(f"Error in ModelPricing#get_retail_prices: {e}")
            logging.error(traceback.format_exc())
            return []

    def price_models(self, models: list[dict], refresh: bool = False) -> list[dict]:
        """
        Return a list of dicts, one per given model (as returned by Models#list_available_models),
        with retail prices in USD per 1M tokens for each of the model's deployment SKUs:
        {"format", "name", "version", "matched", "product",
         "prices": {"GlobalStandard": {"input": 1.25, "cached_input": 0.125, "output": 10.0}, ...},
         "ptu_per_hour": {"GlobalProvisionedManaged": 1.0, ...}, "meters": [...]}
        """
        try:
            items = self.get_retail_prices(refresh)
            meters = [m for m in (self.parse_meter(i) for i in items) if m is not None]
            ptu_prices = self.ptu_prices_by_product(items)
            results = []
            for model in models:
                results.append(self.price_model(model, meters, ptu_prices))
            return results
        except Exception as e:
            logging.error(f"Error in ModelPricing#price_models: {e}")
            logging.error(traceback.format_exc())
            return []

    def price_model(self, model: dict, meters: list[dict], ptu_prices: dict) -> dict:
        name, version = model.get("name", ""), str(model.get("version", ""))
        model_skus = [s.get("name") for s in (model.get("skus") or [])]
        model_key, model_dates = self.model_key(name)
        version_digits = re.sub(r"\D", "", version)
        product_prefixes = FORMAT_PRODUCT_PREFIXES.get(model.get("format"))
        if product_prefixes is not None:
            product_prefixes = product_prefixes + ANY_FORMAT_PRODUCT_PREFIXES

        # best[(sku, token_type)] = (score, meter)
        best = {}
        for meter in meters:
            if meter["key"] != model_key:
                continue
            if product_prefixes is not None and not any(
                (meter["product"] or "").startswith(p) for p in product_prefixes
            ):
                continue
            if meter["dates"]:
                if not all(
                    self.date_matches(d, model_dates, version_digits) for d in meter["dates"]
                ):
                    continue
                score = 2
            else:
                score = 1
            sku = meter["sku"]
            if sku != "*" and sku not in model_skus:
                continue
            k = (sku, meter["token_type"])
            if k not in best or score > best[k][0]:
                best[k] = (score, meter)

        prices = {}
        for (sku, token_type), (_, meter) in sorted(best.items()):
            prices.setdefault(sku, {})[token_type] = meter["price_per_1m"]
        # Meters without a deployment type (e.g. Phi) apply to all of the model's pay-per-token SKUs.
        if "*" in prices:
            generic = prices.pop("*")
            for sku in model_skus:
                if sku in SKU_NAMES.values():
                    prices[sku] = {**generic, **prices.get(sku, {})}

        product = next(iter(best.values()))[1]["product"] if best else None
        ptu = {}
        if product:
            # e.g. "Azure OpenAI GPT5" models use the "Azure OpenAI" PTU meters
            product_ptu = ptu_prices.get(product, {})
            if not product_ptu and product.startswith("Azure OpenAI"):
                product_ptu = ptu_prices.get("Azure OpenAI", {})
            ptu = {s: p for s, p in product_ptu.items() if s in model_skus}
        return {
            "format": model.get("format"),
            "name": name,
            "version": version,
            "matched": len(prices) > 0,
            "product": product,
            "currency": "USD",
            "unit": "1M tokens",
            "prices": prices,
            "ptu_per_hour": ptu,
            "meters": sorted({m["meter_name"] for _, m in best.values()}),
        }

    def parse_meter(self, item: dict) -> dict | None:
        """
        Parse a Retail Prices API item into a dict with the model key, token type
        (input/cached_input/output), and deployment SKU; return None if it's not a
        standard per-token inference meter.
        """
        meter_name = item.get("meterName", "")
        unit = item.get("unitOfMeasure")
        if not meter_name.endswith("Tokens") or unit not in ("1K", "1M"):
            return None
        words = [w for w in re.split(r"[\s\-_]+", meter_name.lower()) if w]
        # "Data Zone" is sometimes written as two words
        text = " ".join(words).replace("data zone", "datazone")
        words = text.split()
        if any(w in SKIP_WORDS or re.fullmatch(r"aud\d+", w) for w in words):
            return None

        cached = any(w in CACHED_WORDS for w in words)
        is_input = any(w in INPUT_WORDS for w in words)
        is_output = any(w in OUTPUT_WORDS for w in words)
        if is_output and not (is_input or cached):
            token_type = "output"
        elif cached:
            token_type = "cached_input"
        elif is_input or "embedding" in words:
            token_type = "input"
        else:
            return None

        deployment = None
        if any(w in GLOBAL_WORDS for w in words):
            deployment = "global"
        elif any(w in DATAZONE_WORDS for w in words):
            deployment = "datazone"
        elif any(w in REGIONAL_WORDS for w in words):
            deployment = "regional"
        batch = "batch" in words
        if deployment is None:
            sku = None if batch else "*"
        else:
            sku = SKU_NAMES.get((deployment, batch))
        if sku is None:
            return None

        classifier_words = (
            CACHED_WORDS
            | INPUT_WORDS
            | OUTPUT_WORDS
            | GLOBAL_WORDS
            | DATAZONE_WORDS
            | REGIONAL_WORDS
            | {"batch"}
        )
        key, dates = self.words_to_key([w for w in words if w not in classifier_words])
        price = float(item.get("retailPrice", 0.0))
        return {
            "meter_name": item.get("meterName"),
            "product": item.get("productName"),
            "key": key,
            "dates": dates,
            "token_type": token_type,
            "sku": sku,
            "price_per_1m": round(price * 1000.0 if unit == "1K" else price, 6),
        }

    def model_key(self, model_name: str) -> tuple[str, list[str]]:
        """Return the (key, dates) for the given model name, for matching to meter keys."""
        name = model_name.lower()
        key, dates = self.words_to_key([w for w in re.split(r"[\s\-_]+", name) if w])
        if name in MODEL_KEY_ALIASES:
            key = MODEL_KEY_ALIASES[name]
        return key, dates

    def words_to_key(self, words: list[str]) -> tuple[str, list[str]]:
        """
        Return a compact matching key from the given words, and the date-like words
        (e.g. 0416, 05052026) which were removed from it.
        """
        dates = [w for w in words if re.fullmatch(r"\d{4}|\d{8}", w)]
        kept = [w for w in words if w not in IGNORE_WORDS and w not in dates]
        return "".join(kept), dates

    def date_matches(self, date: str, model_dates: list[str], version_digits: str) -> bool:
        """
        Return True if the meter date (MMDD, or MMDDYYYY) matches a date in the
        model name, or the model version (e.g. 2025-04-16).
        """
        if date in model_dates:
            return True
        if len(date) == 8:
            return version_digits == date[4:] + date[:4]
        return len(version_digits) == 8 and version_digits.endswith(date)

    def ptu_prices_by_product(self, items: list[dict]) -> dict:
        """Return the provisioned throughput unit (PTU) hourly prices, per product and SKU."""
        ptu = {}
        for item in items:
            sku = PTU_METER_SKUS.get(item.get("meterName"))
            if sku and item.get("unitOfMeasure") == "1/Hour":
                ptu.setdefault(item.get("productName"), {})[sku] = float(
                    item.get("retailPrice", 0.0)
                )
        return ptu
