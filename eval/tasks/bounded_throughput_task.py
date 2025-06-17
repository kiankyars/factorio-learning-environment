from .unbounded_throughput_task import UnboundedThroughputTask

class BoundedThroughputTask(UnboundedThroughputTask):
    def __init__(self, *args, time_limit_seconds=300, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_limit_seconds = time_limit_seconds

    def verify(self, score, instance, step_statistics):
        # Use timing metrics from instance/environment to bound the evaluation
        elapsed = 0
        max_achieved_throughput = 0
        max_achievements = None
        start_time = instance.get_current_time()  # Replace with actual timing metric accessor
        while elapsed < self.time_limit_seconds:
            result_list, result, error, achievements = eval_program_with_achievements(
                program=f"sleep({self.holdout_wait_period})", instance=instance)
            if max_achievements is None:
                max_achievements = achievements
            dynamic_achievements = achievements["dynamic"]
            target_throughput = dynamic_achievements.get(self.throughput_entity, 0)
            if target_throughput > max_achieved_throughput:
                max_achieved_throughput = target_throughput
                max_achievements = achievements
            else:
                break
            elapsed = instance.get_current_time() - start_time  # Update this appropriately
        return TaskResponse(
            success=False,
            meta={"achievements": max_achievements,
                  "seconds_elapsed": elapsed,
                  "time_limit": self.time_limit_seconds,
                  "nr_of_steps_left": self.trajectory_length - step_statistics["current_step_id"] - 1}
        )