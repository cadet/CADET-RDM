from pathlib import Path

from tabulate import tabulate


class OutputLog:
    def __init__(self, filepath=None):
        # ToDo add classmethod for initialization from list of lists
        if not Path(filepath).exists():
            self._entry_list = [[], []]
            self.entries = []
            return

        self._entry_list = self._read_file(filepath)
        self.entries = self._entries_from_entry_list(self._entry_list)

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        try:
            entry = self.entries[self._index]
            self._index += 1
            return entry
        except IndexError:
            raise StopIteration

    def _entries_from_entry_list(self, entry_list):
        header = self._convert_header(entry_list[0])
        if len(header) < 9:
            header.append("options_hash")
        entry_list = entry_list[1:]
        entry_dictionaries = []
        for entry in entry_list:
            if len(entry) < len(header):
                entry += [""] * (len(header) - len(entry))

            entry_dictionaries.append(
                {key: value for key, value in zip(header, entry)}
            )
        return [LogEntry(**entry) for entry in entry_dictionaries]

    def _read_file(self, filepath):
        with open(filepath) as handle:
            lines = handle.readlines()
        lines = [line.replace("\n", "").split("\t") for line in lines]
        return lines

    def _convert_header(self, header):
        return [entry.lower().replace(" ", "_") for entry in header]

    def __str__(self):
        return tabulate(self._entry_list[1:], headers=self._entry_list[0])


class LogEntry:
    def __init__(self, output_repo_commit_message, output_repo_branch, output_repo_commit_hash,
                 project_repo_commit_hash, project_repo_folder_name, project_repo_remotes, python_sys_args, tags,
                 options_hash):
        self.output_repo_commit_message = output_repo_commit_message
        self.output_repo_branch = output_repo_branch
        self.output_repo_commit_hash = output_repo_commit_hash
        self.project_repo_commit_hash = project_repo_commit_hash
        self.project_repo_folder_name = project_repo_folder_name
        self.project_repo_remotes = project_repo_remotes
        self.python_sys_args = python_sys_args
        self.tags = tags
        self.options_hash = options_hash

    def __repr__(self):
        return f"OutputEntry('{self.output_repo_commit_message}', '{self.output_repo_branch}')"


if __name__ == '__main__':
    output_log = OutputLog(filepath=r"C:\Users\ronal\PycharmProjects\CADETRDM\tests\test_repo\results\log.tsv")
    print(output_log.entries)

    output_log = OutputLog(
        filepath=r"C:\Users\ronal\PycharmProjects\CADETRDM\tests\test_repo\results\lognonexistant.tsv")
    print(output_log.entries)
