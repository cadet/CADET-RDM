from cadetrdm import Options
from cadetrdm.wrapper import tracks_results

from runner_repo import setup_optimization_problem, setup_optimizer


@tracks_results
def main(repo, options):
    optimization_problem = setup_optimization_problem(options)
    optimizer = setup_optimizer(optimization_problem, options.optimizer_options)
    results = optimizer.optimize(
        optimization_problem,
        save_results=True,
        use_checkpoint=False,
        results_directory=f"{repo.output_path}/{options.case}",
    )


if __name__ == '__main__':
    options = Options()
    options.debug = False
    options.push = False
    options.commit_message = 'Trying out new things'
    options.case = "FooBar"
    options.optimizer_options = {
        "optimizer": "U_NSGA3",
        "pop_size": 3,
        "n_cores": 3,
        "n_max_gen": 2,
    }
    main(options)
