import os
import platform
import time


class System:
    @classmethod
    def platform_info(cls) -> str:
        """
        Return a string with the platform info including processor.
        Example: macOS-26.4.1-arm64-arm-64bit-Mach-O
        """
        return f"{platform.platform()} : {platform.processor()}"

    @classmethod
    def platform(cls) -> str:
        """
        Return the platform.system() string.
        For example: platform.system() -> 'Darwin'
        """
        return platform.system().lower().strip()

    @classmethod
    def pwd(cls) -> str:
        """
        Return the current working directory.
        """
        return os.getcwd()

    @classmethod
    def is_windows(cls) -> bool:
        """Return True if the platform is Windows, else False."""
        return cls.platform().startswith("win")

    @classmethod
    def is_mac(cls) -> bool:
        """Return True if the platform is Apple macOS, else False."""
        return "darwin" in cls.platform()

    @classmethod
    def is_linux(cls) -> bool:
        """Return True if the platform is linux, else False."""
        return "linux" in cls.platform()

    @classmethod
    def epoch(cls) -> float:
        """
        Return the current epoch time as a float
        """
        return time.time()

    @classmethod
    def epoch_int(cls) -> int:
        """
        Return the current epoch time as an int
        """
        return int(time.time())

    @classmethod
    def user(cls) -> str:
        """
        Return user on the local machine.
        """
        if cls.is_windows():
            value = os.getenv("USERNAME")
            if value is None:
                return "unknown"
            return value
        elif cls.is_mac():
            value = os.getenv("USER")
            if value is None:
                return "unknown"
            return value
        elif cls.is_linux():
            value = os.getenv("USER")
            if value is None:
                return "unknown"
            return value
        else:
            return "unknown"
