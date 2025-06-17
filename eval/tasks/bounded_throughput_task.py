from .unbounded_throughput_task import UnboundedThroughputTask

class BoundedThroughputTask(UnboundedThroughputTask):
    def __init__(self, *args, time_limit_seconds=300, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_limit_seconds = time_limit_seconds

    def verify(self, score, instance, step_statistics):
        # step_statistics or program should be passed in, adapt as needed
        elapsed = 0
        max_achieved_throughput = 0
        max_achievements = None

        # Suppose you have access to a list of all evaluated programs for this agent
        evaluated_programs = step_statistics.get("programs", [])

        for program in evaluated_programs:
            timing_metrics = program.timing_metrics  # This is already populated by TrajectoryRunner
            # You want ONLY the last claude_api_call in each step, per your requirements
            if "claude_api_call" in timing_metrics:
                calls = timing_metrics["claude_api_call"]
                if isinstance(calls, list):
                    elapsed += float(calls[-1])  # Only use the last call's time for each step
                else:
                    elapsed += float(calls)
            # Optionally, accumulate other timings if needed

            # Stop if we've exceeded the budget
            if elapsed >= self.time_limit_seconds:
                break

            # Track throughput as usual (unchanged from UnboundedThroughputTask)
            achievements = program.meta.get("achievements", {})
            dynamic_achievements = achievements.get("dynamic", {})
            target_throughput = dynamic_achievements.get(self.throughput_entity, 0)
            if target_throughput > max_achieved_throughput:
                max_achieved_throughput = target_throughput
                max_achievements = achievements

        return TaskResponse(
            success=False,  # Or True if you want to stop the agent
            meta={
                "achievements": max_achievements,
                "seconds_elapsed": elapsed,
                "time_limit": self.time_limit_seconds,
                "nr_of_steps_left": self.trajectory_length - step_statistics["current_step_id"] - 1
            }
        )