import sys
import time
import os
from pathlib import Path

from cadetrdm.io_utils import wait_for_user
from ipylab import JupyterFrontEnd
import junix
import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.nbconvertapp import NbConvertApp


class Notebook:
    def __init__(self, notebook_path):
        self.notebook_path = Path(notebook_path)

    @property
    def notebook_name(self):
        return str(self.notebook_path.name).replace(".", "_")

    def check_execution_order(self,
                              check_all_executed=False,
                              check_top_to_bottom=False,
                              check_in_order=True,
                              exclude_last_cell=False):
        notebook = nbf.read(self.notebook_path, nbf.NO_CONVERT)

        # extract all code cells (disregard markdown, raw and others), then extract the execution order
        output_cells = [cell for cell in notebook.cells if cell["cell_type"] == "code"]
        # remove empty cells
        non_empty_cells = [cell for cell in output_cells if cell["source"] != ""]
        execution_counts = [cell["execution_count"] for cell in non_empty_cells]

        def _all_none(item_list):
            return all([i is None for i in item_list])

        # return early if no cells were executed
        if _all_none(execution_counts):
            return True

        pass_check = [True]

        def _check_all_executed(execution_counts: list) -> bool:
            """Check all cells were executed.

            Parameters
            ----------
            execution_counts : list
                execution_counts

            Returns
            -------
            bool
            """
            return not None in execution_counts

        def _check_in_order(execution_counts: list) -> bool:
            """Check that execution counts that aren't None go from 1 to N.

            Parameters
            ----------
            execution_counts : list
                execution counts

            Returns
            -------
            bool
            """
            execution_counts = [x for x in execution_counts if x is not None]
            count_range = len(execution_counts) - 1
            if exclude_last_cell:
                count_range = count_range - 1
            print(execution_counts)
            is_in_order = all([execution_counts[i] < execution_counts[i + 1] for i in range(count_range)])
            return is_in_order

        if check_in_order:
            pass_check.append(_check_in_order(execution_counts))

        if check_all_executed:
            pass_check.append(_check_all_executed(execution_counts))

        if check_top_to_bottom:
            pass_check.append(
                _check_all_executed(execution_counts) and _check_in_order(execution_counts)
            )
        return all(pass_check)

    def save_ipynb(self):
        app = JupyterFrontEnd()
        print("Saving", end="")
        # note: docmanager:save doesn't lock the python thread until saving is completed.
        # Sometimes, new changes aren't completely saved before checks are performed.
        # Waiting for 0.1 seconds seems to prevent that.
        app.commands.execute('docmanager:save')
        time.sleep(0.1)
        print("")

    def reload_notebook(self):
        app = JupyterFrontEnd()
        app.commands.execute('docmanager:reload')

    def check_and_rerun_notebook(self, force_rerun=False, timeout=600):
        if "nbconvert_call" in sys.argv:
            return

        self.save_ipynb()
        # wait a second for the save process to finish.
        time.sleep(1)

        is_in_order = self.check_execution_order(exclude_last_cell=False)

        if is_in_order and not force_rerun:
            print("Notebook was already executed in order.")
            return
        else:
            rerun_confirmed_bool = wait_for_user("Notebook was not in order, rerun notebook now?")
            if not rerun_confirmed_bool and not force_rerun:
                print("Aborting.")
                return

        print("Rerunning.")
        with open(self.notebook_path) as f:
            nb = nbf.read(f, as_version=4)

        ep = ExecutePreprocessor(timeout=timeout, kernel_name='python3', extra_arguments=["nbconvert_call"])
        ep.preprocess(nb, )

        with open(self.notebook_path, 'w', encoding='utf-8') as f:
            nbf.write(nb, f)

        self.reload_notebook()

    def convert_ipynb(self, output_dir, formats: list = None):
        if formats is None:
            formats = ["html", ]  # ToDo add ipynb: does this work? or should I copy?
        app = NbConvertApp()
        app.initialize()
        output_root_directory = os.path.join(output_dir, self.notebook_name)
        for export_format in formats:
            app.export_format = export_format
            app.notebooks = [str(self.notebook_path)]
            app.output_base = os.path.join(output_root_directory,
                                           self.notebook_path.name.replace('.ipynb', ''))
            if not os.path.exists(output_root_directory):
                os.makedirs(output_root_directory)
            app.start()

    def export_all_figures(self, output_dir):
        file_without_extension = self.notebook_path.stem
        images = junix.export_images(filepath=str(self.notebook_path),
                                     output_dir=os.path.join(output_dir, self.notebook_name),
                                     prefix=file_without_extension)
