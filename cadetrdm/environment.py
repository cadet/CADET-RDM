import io
import os
import re
from typing import IO, Self

import yaml
from semantic_version import Version, SimpleSpec


class Environment:
    """Conda and pip package requirements of a project."""

    def __init__(
        self,
        *args: object,
        conda_packages: dict[str, str] | None = None,
        pip_packages: dict[str, str] | None = None,
        name: str | None = None,
        channels: list[str] | None = None,
    ) -> None:
        if args:
            raise TypeError(
                "Environment.__init__() does not take positional arguments. "
                "Please specify conda_packages and/or pip_packages."
            )
        self.conda_packages = conda_packages
        self.pip_packages = pip_packages
        self.packages = dict()
        if conda_packages:
            self.packages.update(conda_packages)
        if pip_packages:
            self.packages.update(pip_packages)

        self.name = name
        self.channels = channels

    @classmethod
    def from_yml(cls, yml_path: str | os.PathLike) -> Self:
        """
        Create an Environment object from a YAML file.

        Parameters
        ----------
        yml_path : str | os.PathLike
            Path to a conda environment.yml file.

        Returns
        -------
        Environment
            Environment described by the file.
        """
        with open(yml_path, encoding="utf-8") as handle:
            yml_string = "".join(handle.readlines())

        instance = cls.from_yml_string(yml_string)
        return instance

    @classmethod
    def from_yml_string(cls, yml_string: str) -> Self:
        """
        Create an Environment object from a YAML string.

        Parameters
        ----------
        yml_string : str
            Content of a conda environment.yml file.

        Returns
        -------
        Environment
            Environment described by the string.
        """
        # Remove special formatting characters from the string
        ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        yml_string = re.sub(ansi_escape_pattern, "", yml_string)

        packages = yaml.safe_load(yml_string)

        instance = cls()

        # If for some reason the environment.yml is empty, return an empty instance
        if packages is None:
            return instance

        instance.name = packages.get("name")
        instance.channels = packages.get("channels")

        # Some historical environment.yml files (recorded by older cadetrdm
        # versions, or other yaml content sharing this loader) don't have a
        # "dependencies" key at all - treat that the same as an empty
        # environment instead of crashing, matching the "packages is None"
        # case above.
        dependencies = packages.get("dependencies")
        if not dependencies:
            return instance

        conda_packages = {
            line.split("=")[0]: line.split("=")[1]
            for line in dependencies if isinstance(line, str)
        }
        instance.packages.update(conda_packages)
        instance.conda_packages = conda_packages

        if isinstance(dependencies[-1], dict) and "pip" in dependencies[-1]:
            pip_packages = dependencies[-1]["pip"]
            pip_packages = {line.split("==")[0]: line.split("==")[1] for line in pip_packages}
            instance.packages.update(pip_packages)
            instance.pip_packages = pip_packages

        return instance

    def to_yml(self, handle: IO[str]) -> None:
        """
        Write the environment as an environment.yml file.

        Parameters
        ----------
        handle : IO[str]
            Writable text handle.
        """
        yml_dict = self._to_yml_dict()

        yaml.safe_dump(yml_dict, handle)

    def _to_yml_dict(self) -> dict:
        """
        Create an environment.yml type yml dict from an Environment instance.

        Returns
        -------
        dict
            Dictionary with name, channels and dependencies.
        """
        dependency_list = []
        if self.conda_packages is not None:
            for package, spec in self.conda_packages.items():
                if "git+" in spec:
                    raise ValueError(f"Conda can not use git+ dependencies for {package} {spec}")
                elif ">" in spec or "<" in spec or "=" in spec:
                    dependency_list.append(f"{package}{spec}")
                else:
                    dependency_list.append(f"{package}={spec}")

        pip_list = []
        if self.pip_packages is not None:
            for package, spec in self.pip_packages.items():
                if "git+" in spec:
                    pip_list.append(spec)
                elif ">" in spec or "<" in spec or "=" in spec:
                    pip_list.append(f"{package}{spec}")
                else:
                    pip_list.append(f"{package}=={spec}")

            dependency_list.append({"pip": pip_list})

        yml_dict = {
            "name": self.name,
            "channels": self.channels,
            "dependencies": dependency_list,
        }
        return yml_dict

    def update(self, environment: Self) -> None:
        """
        Update name, channels and packages with those of another environment.

        Parameters
        ----------
        environment : Environment
            Environment whose entries take precedence.
        """
        if environment.name is not None:
            self.name = environment.name
        if environment.channels is not None:
            self.channels = environment.channels
        self.conda_packages.update(environment.conda_packages)
        self.pip_packages.update(environment.pip_packages)

    def package_version(self, package: str) -> str | None:
        """
        Return the version specification of a package.

        Parameters
        ----------
        package : str
            Package name.

        Returns
        -------
        str | None
            Version specification, or None if the package is not part of the environment.
        """
        if package not in self.packages:
            return None

        return self.packages[package]

    def fulfils(self, package: str, version: str) -> bool:
        """
        Check if the installed version of a package matches the specified version.

        Uses semantic versioning to compare the versions.

        Parameters
        ----------
        package : str
            The name of the package to check.
        version : str
            The version or specification string to match against.

        Returns
        -------
        bool
            True if the installed package version matches the specified version,
            False otherwise.

        Examples
        --------
        >>> env.fulfils("conda", ">=0.1.1")  # larger or equal
        >>> env.fulfils("conda", "~0.1.1")  # tolerant of pre-release suffixes
        >>> env.fulfils("conda", "0.1.1")  # exactly equal, including pre-release suffixes
        """
        installed_version = self.package_version(package)
        if installed_version is None:
            return False

        if "git+" in installed_version:
            return False

        # Use .coerce instead of .parse to ensure non-standard version strings are converted.
        # Rules are:
        #   - If no minor or patch component, and partial is False, replace them with zeroes
        #   - Any character outside of a-zA-Z0-9.+- is replaced with a -
        #   - If more than 3 dot-separated numerical components,
        #       everything from the fourth component belongs to the build part
        #   - Any extra + in the build part will be replaced with dots
        installed_version = Version.coerce(installed_version)

        try:
            spec = SimpleSpec(version)
        except ValueError as e:
            spec = SimpleSpec(str(Version.coerce(version)))
            print(
                f"Warning: {e} when processing {package}={version}. "
                f"Using {str(Version.coerce(version))} instead."
            )

        match = spec.match(installed_version)

        return match

    def fulfils_environment(self, environment: Self | None) -> bool:
        """
        Check if this environment fulfils the requirements in a given environment.

        Parameters
        ----------
        environment : Environment | None
            Environment with requirements as key: value pairs.
            If None, the requirements are always fulfilled.

        Returns
        -------
        bool
            True if all requirements are fulfilled.
        """
        if environment is None:
            return True

        mismatches = []

        for package, version in environment.packages.items():
            try:
                if not self.fulfils(package, version):
                    mismatches.append((package, version, self.package_version(package)))
            except ValueError:
                mismatches.append((package, version, self.package_version(package)))

        if mismatches:
            for package, version, existing_version in mismatches:
                print(
                    f"Package {package}: {existing_version} "
                    f"does not fulfil requirements: {version}"
                )
            return False

        return True

    def __repr__(self) -> str:
        """Return the conda and pip packages as constructor arguments."""
        return (f"Environment("
                f"conda_packages = {repr(self.conda_packages)},  "
                f"pip_packages = {repr(self.pip_packages)}"
                f")")

    def __str__(self) -> str:
        """Return the environment in environment.yml format."""
        handle = io.StringIO()
        yaml.safe_dump(self._to_yml_dict(), handle)
        return "Environment:\n" + handle.getvalue()
