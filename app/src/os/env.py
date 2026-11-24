import logging
import os
import sys
import time

# This class is used to read the host environment variables.
# It also has methods for command-line flag argument processing.

# Values of environment variables whose names contain one of these are masked when logged,
# since the container logs go to Log Analytics and Application Insights.
SECRET_NAME_PARTS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CONNECTION_STRING", "IDENTITY_HEADER")


class Env:
    @classmethod
    def envvar(cls, name: str, default=None) -> str:
        """
        Return the value of the given environment variable name,
        or the given default value.
        """
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            return str(default)
        return ""

    @classmethod
    def boolean_arg(cls, flag_arg: str) -> bool:
        """
        Return a boolean indicating if the given arg is in the command-line.
        """
        return flag_arg in sys.argv

    @classmethod
    def username(cls) -> str | None:
        """
        Return the USERNAME (Windows) or USER (macOS/Linux) value.
        """
        user = cls.envvar("USERNAME")
        if user is None:
            user = cls.envvar("USER")
        return user

    @classmethod
    def epoch(cls) -> float:
        """
        Return the current epoch time as a float
        """
        return time.time()

    @classmethod
    def verbose(cls) -> bool:
        """
        Return a boolean indicating if --verbose is in the command-line.
        """
        return "--verbose" in sys.argv

    # Azure Document Intelligence methods below

    @classmethod
    def document_intelligence_supported_filetypes(cls) -> list[str]:
        """
        Return the filetypes supported by Document Intelligence.
        Filetypes: bmp, docx, heif, html, jpeg, jpg, md, pdf, png, pptx, tiff, xlsx
        """
        general_types = "pdf,html"
        images_types = "jpeg,jpg,png,bmp,heif,tiff"
        ms_office_types = "docx,xlsx,pptx"
        all_types = f"{general_types},{images_types},{ms_office_types}"
        return sorted(all_types.lower().strip().split(","))

    # Environment variable metadatamethods below

    @classmethod
    def log_env_vars(cls, redact_secrets: bool = True) -> bool:
        for name in sorted(os.environ.keys()):
            value = cls.envvar(name)
            if redact_secrets == True:
                if any(part in name.upper() for part in SECRET_NAME_PARTS):
                    value = "***"
            logging.warning("envvar: {} -> {}".format(name, value))
        return True

    @classmethod
    def log_standard_env_vars(cls) -> bool:
        for key in sorted(cls.standard_env_vars().keys()):
            value = cls.envvar(key)
            logging.warning("envvar: {} -> {}".format(key, value))
        return True

    @classmethod
    def standard_env_vars(cls) -> dict:
        d = dict()
        d["AZURE_AI_SEARCH_URL"] = "Azure AI Search service URL"
        d["AZURE_STORAGE_ACCOUNT_URL"] = "Azure Storage account Blob service URL"
        d["LOG_LEVEL"] = "A standard python or java logging level name."

        return d

    @classmethod
    def set_unit_testing_environment(cls):
        """
        This method is for uniting-testing purposed only.
        It sets sys.argv, and certain environment variables
        for consistent test results.
        See test_env.py for example usage.
        """
        sys.argv.append("--some-flag")
        sys.argv.append("--some-int")
        sys.argv.append("42")
        sys.argv.append("--some-float")
        sys.argv.append("3.1415926")
        sys.argv.append("--some-float")
        sys.argv.append("--verbose")
        return True

    @classmethod
    def azure_ai_search_name(cls) -> str:
        return cls.envvar("AZURE_AI_SEARCH_NAME", None)

    @classmethod
    def azure_ai_search_region(cls) -> str:
        return cls.envvar("AZURE_AI_SEARCH_REGION", "southcentralus")

    @classmethod
    def azure_ai_search_url(cls) -> str:
        return cls.envvar("AZURE_AI_SEARCH_URL", None)

    @classmethod
    def azure_ai_search_version(cls) -> str:
        return cls.envvar("AZURE_AI_SEARCH_VERSION", "2025-09-01")

    @classmethod
    def azure_app_insights_app(cls) -> str:
        return cls.envvar("AZURE_APP_INSIGHTS_APP", None)

    @classmethod
    def azure_app_insights_connection_string(cls) -> str:
        return cls.envvar("AZURE_APP_INSIGHTS_CONNECTION_STRING", None)

    @classmethod
    def azure_app_insights_instrumentation_key(cls) -> str:
        return cls.envvar("AZURE_APP_INSIGHTS_INSTRUMENTATION_KEY", None)

    @classmethod
    def azure_app_insights_key(cls) -> str:
        return cls.envvar("AZURE_APP_INSIGHTS_KEY", None)

    @classmethod
    def azure_default_region(cls) -> str:
        return cls.envvar("AZURE_DEFAULT_REGION", "southcentralus")

    @classmethod
    def azure_directory(cls) -> str:
        return cls.envvar("AZURE_DIRECTORY", None)

    @classmethod
    def azure_docintel_acct(cls) -> str:
        return cls.envvar("AZURE_DOCINTEL_ACCT", None)

    @classmethod
    def azure_docintel_key(cls) -> str:
        return cls.envvar("AZURE_DOCINTEL_KEY", None)

    @classmethod
    def azure_docintel_url(cls) -> str:
        return cls.envvar("AZURE_DOCINTEL_URL", None)

    @classmethod
    def azure_foundry_aisvcs_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_AISVCS_URL", None)

    @classmethod
    def azure_foundry_customvoice_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_CUSTOMVOICE_URL", None)

    @classmethod
    def azure_foundry_doctrans_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_DOCTRANS_URL", None)

    @classmethod
    def azure_foundry_key(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_KEY", None)

    @classmethod
    def azure_foundry_key2(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_KEY2", None)

    @classmethod
    def azure_foundry_name(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_NAME", None)

    @classmethod
    def azure_foundry_oai_dalleapi(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_OAI_DALLEAPI", None)

    @classmethod
    def azure_foundry_oai_langapi_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_OAI_LANGAPI_URL", None)

    @classmethod
    def azure_foundry_oai_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_OAI_URL", None)

    @classmethod
    def azure_foundry_oai_whisperapi_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_OAI_WHISPERAPI_URL", None)

    @classmethod
    def azure_foundry_openai_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_OPENAI_URL", None)

    @classmethod
    def azure_foundry_project1_key(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_PROJECT1_KEY", None)

    @classmethod
    def azure_foundry_project_key(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_PROJECT_KEY", None)

    @classmethod
    def azure_foundry_project_name(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_PROJECT_NAME", None)

    @classmethod
    def azure_foundry_project_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_PROJECT_URL", None)

    @classmethod
    def azure_foundry_region(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_REGION", "southcentralus")

    @classmethod
    def azure_foundry_rg(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_RG", None)

    @classmethod
    def azure_foundry_speech2text_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_SPEECH2TEXT_URL", None)

    @classmethod
    def azure_foundry_text2speech_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_TEXT2SPEECH_URL", None)

    @classmethod
    def azure_foundry_texttrans_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_TEXTTRANS_URL", None)

    @classmethod
    def azure_foundry_url(cls) -> str:
        return cls.envvar("AZURE_FOUNDRY_URL", None)

    @classmethod
    def azure_langservice_acct(cls) -> str:
        return cls.envvar("AZURE_LANGSERVICE_ACCT", None)

    @classmethod
    def azure_langservice_key(cls) -> str:
        return cls.envvar("AZURE_LANGSERVICE_KEY", None)

    @classmethod
    def azure_langservice_region(cls) -> str:
        return cls.envvar("AZURE_LANGSERVICE_REGION", "southcentralus")

    @classmethod
    def azure_langservice_url(cls) -> str:
        return cls.envvar("AZURE_LANGSERVICE_URL", None)

    @classmethod
    def azure_mongo_utils_data_dir(cls) -> str:
        return cls.envvar("AZURE_MONGO_UTILS_DATA_DIR", None)

    @classmethod
    def azure_openai_completions_dep(cls) -> str:
        return cls.envvar("AZURE_OPENAI_COMPLETIONS_DEP", None)

    @classmethod
    def azure_openai_completions_key(cls) -> str:
        return cls.envvar("AZURE_OPENAI_COMPLETIONS_KEY", None)

    @classmethod
    def azure_openai_completions_url(cls) -> str:
        return cls.envvar("AZURE_OPENAI_COMPLETIONS_URL", None)

    @classmethod
    def azure_openai_embeddings_dep(cls) -> str:
        return cls.envvar("AZURE_OPENAI_EMBEDDINGS_DEP", None)

    @classmethod
    def azure_openai_embeddings_key(cls) -> str:
        return cls.envvar("AZURE_OPENAI_EMBEDDINGS_KEY", None)

    @classmethod
    def azure_openai_embeddings_url(cls) -> str:
        return cls.envvar("AZURE_OPENAI_EMBEDDINGS_URL", None)

    @classmethod
    def azure_openai_key(cls) -> str:
        return cls.envvar("AZURE_OPENAI_KEY", None)

    @classmethod
    def azure_openai_name(cls) -> str:
        return cls.envvar("AZURE_OPENAI_NAME", None)

    @classmethod
    def azure_openai_region(cls) -> str:
        return cls.envvar("AZURE_OPENAI_REGION", "southcentralus")

    @classmethod
    def azure_openai_url(cls) -> str:
        return cls.envvar("AZURE_OPENAI_URL", None)

    @classmethod
    def azure_rg(cls) -> str:
        return cls.envvar("AZURE_RG", None)

    @classmethod
    def azure_storage_account_name(cls) -> str:
        return cls.envvar("AZURE_STORAGE_ACCOUNT_NAME", None)

    @classmethod
    def azure_storage_account_url(cls) -> str:
        return cls.envvar("AZURE_STORAGE_ACCOUNT_URL", None)

    @classmethod
    def azure_cosmosdb_nosql_uri(cls) -> str:
        return cls.envvar("AZURE_COSMOSDB_NOSQL_URI", None)

    @classmethod
    def azure_cosmosdb_nosql_key(cls) -> str:
        return cls.envvar("AZURE_COSMOSDB_NOSQL_KEY", None)

    @classmethod
    def azure_cosmosdb_authtype(cls) -> str:
        return cls.envvar("AZURE_COSMOSDB_NOSQL_AUTHTYPE", "entra")

    @classmethod
    def azure_subscription_id(cls) -> str:
        return cls.envvar("AZURE_SUBSCRIPTION_ID", None)

    @classmethod
    def azure_subscription_name(cls) -> str:
        return cls.envvar("AZURE_SUBSCRIPTION_NAME", None)
