from fire import Fire


class Workflows:

    def tesla(self):
        from dflow_galaxy.workflow.tesla.main import cmd_entry
        return cmd_entry


class CliRoot:
    """
    DFlow Galaxy CLI Tool
    """

    def workflow(self):
        return Workflows()


def main():
    Fire(CliRoot())


if __name__ == '__main__':
    main()