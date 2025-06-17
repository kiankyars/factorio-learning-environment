from .unbounded_throughput_task import UnboundedThroughputTask

class BoundedThroughputTask(UnboundedThroughputTask):
    def __init__(self, *args, time_limit_seconds=300, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_limit_seconds = time_limit_seconds
        self.elapsed_compute_time = 0  # track cumulative time

    def verify(self, score, instance, step_statistics):
        # Get timing metrics for the current step
        all_metrics = step_statistics.get("timing_metrics", [])
        used_time = get_last_successful_llm_api_call_duration(all_metrics)
        self.elapsed_compute_time += used_time
        time_left = max(0, self.time_limit_seconds - self.elapsed_compute_time)

        # Usual throughput/achievements logic
        max_achievements = ... # your logic
        number_of_steps_left = self.trajectory_length - step_statistics["current_step_id"] - 1
        return TaskResponse(
            success=(time_left <= 0),
            meta={
                "achievements": max_achievements,
                "time_left": time_left,
                "nr_of_steps_left": number_of_steps_left,
            }
        )

    def enhance_response_with_task_output(self, response: str, task_response: TaskResponse) -> str:
        response = super().enhance_response_with_task_output(response, task_response)
        time_left = task_response.meta.get("time_left", None)
        if time_left is not None:
            response += f"\n\n⏳ Time left: {int(time_left)} seconds"
        return response

def get_last_successful_llm_api_call_duration(metrics: list) -> float:
    api_ops = ["claude_api_call", "open_router_api_call", "deepseek_api_call", "gemini_api_call",
               "together_api_call", "o1_mini_api_call"]
    def flatten(metrics):
        for metric in metrics:
            yield metric
            yield from flatten(metric.get("children", []))
    api_calls = [m for m in flatten(metrics) if m["operation"] in api_ops]
    for m in reversed(api_calls):
        http_code = m.get("metadata", {}).get("http_status")
        if http_code == 200:
            return m["duration"]
    if api_calls:
        return api_calls[-1]["duration"]
    return 0.0