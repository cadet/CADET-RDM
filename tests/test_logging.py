import io
import subprocess

import pytest

from cadetrdm import Environment
from cadetrdm.logging import OutputLog


def test_environment_from_yml():
    yml_string = (
        'name: cadetrdmpy3.11\n'
        'channels:\n  - conda-forge\n'
        'dependencies:\n'
        '  - bzip2=1.0.8=hcfcfb64_5\n'
        '  - ca-certificates=2024.12.14=h56e8100_0\n  - cadet=4.4.0=hdf1ca3b_1\n'
        '  - hdf5=1.14.3=nompi_h73e8ff5_100\n  - intel-openmp=2024.0.0=h57928b3_49841\n'
        '  - krb5=1.21.2=heb0366b_0\n  - libaec=1.1.2=h63175ca_1\n  - libblas=3.9.0=21_win64_mkl\n'
        '  - libcblas=3.9.0=21_win64_mkl\n  - libcurl=8.5.0=hd5e4a3a_0\n  - libexpat=2.6.1=h63175ca_0\n'
        '  - libffi=3.4.2=h8ffe710_5\n  - libhwloc=2.9.3=default_haede6df_1009\n  - libiconv=1.17=hcfcfb64_2\n'
        '  - liblapack=3.9.0=21_win64_mkl\n  - liblapacke=3.9.0=21_win64_mkl\n'
        '  - libsqlite=3.45.2=hcfcfb64_0\n  - libssh2=1.11.0=h7dfc565_0\n'
        '  - libxml2=2.12.5=hc3477c8_0\n  - libzlib=1.2.13=hcfcfb64_5\n  - mkl=2024.0.0=h66d3029_49657\n'
        '  - openssl=3.4.0=ha4e3fda_1\n  - pip=24.0=pyhd8ed1ab_0\n  - pthreads-win32=2.9.1=hfa6e2cd_3\n'
        '  - python=3.11.8=h2628c8c_0_cpython\n  - python_abi=3.11=5_cp311\n'
        '  - suitesparse=5.4.0=h5d0cbe0_1\n  - tbb=2021.11.0=h91493d7_1\n  - tbb-devel=2021.11.0=h3ec46f0_1\n'
        '  - tk=8.6.13=h5226925_1\n  - ucrt=10.0.22621.0=h57928b3_0\n  - vc=14.3=hcf57466_18\n'
        '  - vc14_runtime=14.38.33130=h82b7239_18\n  - vs2015_runtime=14.38.33130=hcb4865c_18\n'
        '  - wheel=0.42.0=pyhd8ed1ab_0\n  - xz=5.2.6=h8d14728_0\n  - yaml=0.2.5=h8ffe710_2\n'
        '  - pip:\n'
        '      - about-time==4.2.1\n      - addict==2.3.0\n      - alive-progress==3.1.5\n'
        '      - annotated-types==0.6.0\n      - anyio==4.3.0\n      - appdirs==1.4.4\n'
        '      - arviz==0.17.0\n      - asttokens==2.4.1\n      - attrs==23.2.0\n      - autograd==1.6.2\n'
        '      - betterproto==2.0.0b6\n      - build==1.1.1\n      - cadet-process==0.9.1\n'
        '      - cadet-python==0.14.1\n      - cadet-rdm==0.0.41\n      - certifi==2024.2.2\n'
        '      - cffi==1.16.0\n      - cfgv==3.4.0\n      - charset-normalizer==3.3.2\n'
        '      - click==8.1.7\n      - cma==3.2.2\n      - cobra==0.29.0\n      - colorama==0.4.6\n'
        '      - contourpy==1.2.0\n      - corner==2.2.2\n      - cryptography==42.0.5\n'
        '      - cycler==0.12.1\n      - decorator==5.1.1\n      - depinfo==2.2.0\n'
        '      - deprecated==1.2.14\n      - dill==0.3.8\n      - diskcache==5.6.3\n'
        '      - distlib==0.3.8\n      - docker==7.1.0\n      - executing==2.0.1\n'
        '      - filelock==3.13.1\n      - flake8==7.0.0\n      - fonttools==4.49.0\n'
        '      - future==1.0.0\n      - git-lfs==1.6\n      - gitdb==4.0.11\n      - gitpython==3.1.42\n'
        '      - grapheme==0.6.0\n      - grpclib==0.4.7\n      - h11==0.14.0\n      - h2==4.1.0\n'
        '      - h5netcdf==1.3.0\n      - h5py==3.10.0\n      - hagelkorn==1.2.3\n      - hopsy==1.4.1\n'
        '      - hpack==4.0.0\n      - httpcore==1.0.4\n      - httpx==0.27.0\n      - hyperframe==6.0.1\n'
        '      - identify==2.5.35\n      - idna==3.6\n      - importlib-metadata==7.0.2\n'
        '      - importlib-resources==6.3.0\n      - iniconfig==2.0.0\n      - ipython==8.25.0\n'
        '      - jaraco-classes==3.3.1\n      - jedi==0.19.1\n      - joblib==1.3.2\n'
        '      - keyring==24.3.1\n      - kiwisolver==1.4.5\n      - llvmlite==0.42.0\n'
        '      - markdown-it-py==3.0.0\n      - matplotlib==3.8.3\n      - matplotlib-inline==0.1.7\n'
        '      - mcbackend==0.5.2\n      - mccabe==0.7.0\n      - mdurl==0.1.2\n'
        '      - more-itertools==10.2.0\n      - mpmath==1.3.0\n      - multidict==6.0.5\n'
        '      - multiprocess==0.70.16\n      - nodeenv==1.8.0\n      - numba==0.59.0\n'
        '      - numpy==1.26.4\n      - optlang==1.8.1\n      - packaging==24.0\n      - pandas==2.2.1\n'
        '      - parso==0.8.4\n      - pathos==0.3.2\n      - pillow==10.2.0\n      - platformdirs==4.2.0\n'
        '      - pluggy==1.4.0\n      - polyround==0.2.11\n      - pox==0.3.4\n      - ppft==1.7.6.8\n'
        '      - pre-commit==3.6.2\n      - prompt-toolkit==3.0.47\n      - psutil==6.0.0\n'
        '      - pure-eval==0.2.2\n      - pycodestyle==2.11.1\n      - pycparser==2.21\n'
        '      - pydantic==2.6.4\n      - pydantic-core==2.16.3\n      - pyflakes==3.2.0\n'
        '      - pygithub==2.2.0\n      - pygments==2.17.2\n      - pyjwt==2.8.0\n      - pymoo==0.6.1.1\n'
        '      - pynacl==1.5.0\n      - pyparsing==3.1.2\n      - pypiwin32==223\n'
        '      - pyproject-hooks==1.0.0\n      - pyqt5==5.15.10\n      - pyqt5-qt5==5.15.2\n'
        '      - pyqt5-sip==12.13.0\n      - pytest==8.1.1\n      - python-benedict==0.33.2\n'
        '      - python-dateutil==2.9.0.post0\n      - python-fsutil==0.13.1\n      - python-gitlab==4.4.0\n'
        '      - python-libsbml==5.20.2\n      - python-slugify==8.0.4\n      - pytz==2024.1\n'
        '      - pywin32==306\n      - pywin32-ctypes==0.2.2\n      - pyyaml==6.0.1\n'
        '      - requests==2.31.0\n      - requests-toolbelt==1.0.0\n      - rich==13.7.1\n'
        '      - ruamel-yaml==0.18.6\n      - ruamel-yaml-clib==0.2.8\n      - scikit-learn==1.4.1.post1\n'
        '      - scipy==1.12.0\n      - setuptools==69.2.0\n      - six==1.16.0\n      - smmap==5.0.1\n'
        '      - sniffio==1.3.1\n      - stack-data==0.6.3\n      - swiglpk==5.0.10\n      - sympy==1.12\n'
        '      - tabulate==0.9.0\n      - text-unidecode==1.3\n      - threadpoolctl==3.3.0\n'
        '      - tqdm==4.66.2\n      - traitlets==5.14.3\n      - typing-extensions==4.10.0\n'
        '      - tzdata==2024.1\n      - urllib3==2.2.1\n      - virtualenv==20.25.1\n'
        '      - wcwidth==0.2.13\n      - wrapt==1.16.0\n      - xarray==2024.2.0\n'
        '      - xarray-einstats==0.7.0\n      - zipp==3.18.0\n'
        'prefix: C:\\Users\\ronal\\mambaforge\\envs\\cadetrdmpy3.11\n'
    )

    environment = Environment.from_yml_string(yml_string)
    assert environment.package_version("cadet") == "4.4.0"
    assert environment.fulfils("cadet", "~4.4.0")
    assert not environment.fulfils("cadet", ">4.4.0")
    assert environment.fulfils_environment(environment)

    requirements = {
        "text-unidecode": "1.3",
        "xarray": "<=2024.2.0",
        "zipp": "==3.18"
    }
    fulfilled_requirements = Environment(conda_packages={"cadet": ">=4.4.0"}, pip_packages=requirements)
    fulfilled_requirements.pip_packages["scikit-learn"] = "~1.4.1"

    assert environment.fulfils_environment(fulfilled_requirements)

    instructions = ("conda install -y cadet>=4.4.0 && "
                    "pip install 'text-unidecode==1.3' 'xarray<=2024.2.0' 'zipp==3.18' 'scikit-learn=1.4.1'")
    assert instructions == fulfilled_requirements.prepare_install_instructions()

    not_fulfilled_requirements = Environment(conda_packages={"cadet": ">=4.4.0"}, pip_packages={"xarray": ">=2026.2.0"})

    assert not environment.fulfils_environment(not_fulfilled_requirements)

    # test that the no-requirements case is always fulfilled.
    assert environment.fulfils_environment(None)

    # test eval() reproducibility
    assert environment.fulfils_environment(eval(repr(environment)))
    assert eval(repr(environment)).fulfils_environment(environment)


def test_environment():
    environment = Environment(conda_packages={"cadet": "4.4.0", "tbb": "2024.0.0"}, pip_packages={"xarray": "2024.2.0"})
    assert environment.package_version("cadet") == "4.4.0"
    assert environment.fulfils("cadet", "~4.4.0")
    assert not environment.fulfils("cadet", ">4.4.0")

    install_instructions = "conda install -y cadet=4.4.0 tbb=2024.0.0 && pip install 'xarray==2024.2.0'"
    assert environment.prepare_install_instructions() == install_instructions

    yml_dict = {'name': None,
                'channels': None,
                'dependencies': ['cadet=4.4.0',
                                 'tbb=2024.0.0',
                                 {'pip': ['xarray==2024.2.0']}]}
    assert environment._to_yml_dict() == yml_dict
    yml_string = ('channels: null\ndependencies:\n- cadet=4.4.0\n- tbb=2024.0.0\n'
                  '- pip:\n  - xarray==2024.2.0\nname: null\n')
    handle = io.StringIO()
    environment.to_yml(handle)
    assert yml_string == handle.getvalue()

    environment = Environment(conda_packages=None, pip_packages={"xarray": "2024.2.0"})
    yml_dict = {'name': None,
                'channels': None,
                'dependencies': [{'pip': ['xarray==2024.2.0']}]}
    assert environment._to_yml_dict() == yml_dict

    environment = Environment(conda_packages={"cadet": "4.4.0", "tbb": "2024.0.0"}, pip_packages=None)
    yml_dict = {'name': None,
                'channels': None,
                'dependencies': ['cadet=4.4.0', 'tbb=2024.0.0']}
    assert environment._to_yml_dict() == yml_dict

    complex_environment = Environment(
        conda_packages={"cadet": ">4.4.0", "tbb": ">=2024.0.0", "mkl": "~2024.0.0"},
        pip_packages={"xarray": ">2024.2.0", "pydantic": "<=2.6.4", }
    )

    install_instructions = ("conda install -y cadet>4.4.0 tbb>=2024.0.0 mkl=2024.0.0 && "
                            "pip install 'xarray>2024.2.0' 'pydantic<=2.6.4'")

    assert complex_environment.prepare_install_instructions() == install_instructions


@pytest.mark.slow
def test_update_environment():
    subprocess.run(f'conda env remove -n testing_env_cadet_rdm  -y', shell=True)
    subprocess.run(f'conda create -n testing_env_cadet_rdm python=3.11 -y', shell=True)
    target_env = Environment(
        conda_packages={"libiconv": "1.17", "openssl": ">=3.3"},
        # Currently not aware of any way of activating a conda env and then running commands in it. Therefore,
        # pip requirements are excluded from this test.
        # pip_packages={"cadet-rdm": "0.0.44"}
    )

    check = subprocess.run("conda env export -n testing_env_cadet_rdm ", shell=True, capture_output=True)
    current_env = Environment.from_yml_string(check.stdout.decode())
    assert not current_env.fulfils_environment(target_env)

    install_instructions = target_env.prepare_install_instructions()
    install_instructions = install_instructions.replace("install -y", "install --name testing_env_cadet_rdm -y")
    print(install_instructions)
    subprocess.run(install_instructions, shell=True)

    check = subprocess.run("conda env export -n testing_env_cadet_rdm ", shell=True, capture_output=True)
    current_env = Environment.from_yml_string(check.stdout.decode())
    assert current_env.fulfils_environment(target_env)
