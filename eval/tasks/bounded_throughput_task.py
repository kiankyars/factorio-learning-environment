from typing import Any, Dict, List, Union, Optional
from env.src.entities import Inventory, Entity
from env.src.instance import FactorioInstance
from eval.tasks.unbounded_throughput_task import UnboundedThroughputTask
from agents import TaskResponse

def get_last_successful_llm_api_call_duration(metrics):
    """Extract duration from the last successful LLM API call (HTTP 200)"""
    def flatten(metrics):
        for metric in metrics:
            yield metric
            yield from flatten(metric.get("children", []))
    
    api_calls = [m for m in flatten(metrics) if m["operation"].endswith("_api_call")]
    # Prefer HTTP 200, else just last
    for m in reversed(api_calls):
        http_code = m.get("metadata", {}).get("http_status")
        if http_code == 200 or http_code is None:  # fallback if status missing
            return m["duration"]
    if api_calls:
        return api_calls[-1]["duration"]
    return 0.0

class BoundedThroughputTask(UnboundedThroughputTask):
    def __init__(self, trajectory_length, goal_description: str, task_key: str,
                 throughput_entity: Entity, time_limit_seconds: float,
                 holdout_wait_period: int, pre_holdout_wait_period: int = 0,
                 show_number_of_steps_left_in_prompt=False,
                 include_stats=True, use_populated_inventory=True,
                 unlock_all_research=True, agent_instructions: Optional[List[str]] = None) -> None:
        
        # Add time constraint to goal description
        time_constraint_msg = f"\n\n⏳ CRITICAL TIME CONSTRAINT: You have {int(time_limit_seconds)} seconds of real compute time to complete this task. Every API call consumes from your time budget. Plan efficiently!"
        goal_description += time_constraint_msg
        
        super().__init__(trajectory_length, goal_description, task_key, throughput_entity,
                        holdout_wait_period, pre_holdout_wait_period,
                        show_number_of_steps_left_in_prompt, include_stats,
                        use_populated_inventory, unlock_all_research, agent_instructions)
        
        self.time_limit_seconds = time_limit_seconds
        self.elapsed_compute_time = 0.0  # track cumulative API call time
    
    def verify(self, score: float, instance: FactorioInstance, step_statistics: Dict) -> TaskResponse:
        # Extract timing metrics and update compute time budget
        timing_metrics = step_statistics.get("timing_metrics", [])
        api_call_duration = get_last_successful_llm_api_call_duration(timing_metrics)
        self.elapsed_compute_time += api_call_duration
        
        time_remaining = max(0, self.time_limit_seconds - self.elapsed_compute_time)
        time_budget_exhausted = time_remaining <= 0
        
        # Get throughput achievements as in parent class
        max_achieved_throughput = 0
        max_achievements = None
        
        # Skip throughput evaluation if time is up
        if not time_budget_exhausted:
            while True:
                from env.src.utils.achievements import eval_program_with_achievements
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
        else:
            # Time exhausted - use last known state
            max_achievements = {"dynamic": {self.throughput_entity: 0}}
        
        return TaskResponse(
            success=time_budget_exhausted,  # Task ends when time runs out
            meta={
                "achievements": max_achievements,
                "nr_of_steps_left": self.trajectory_length - step_statistics["current_step_id"] - 1,
                "time_remaining": time_remaining,
                "elapsed_compute_time": self.elapsed_compute_time,
                "time_budget_exhausted": time_budget_exhausted,
                "max_achieved_throughput": max_achieved_throughput
            }
        )
    
    def enhance_response_with_task_output(self, response: str, task_response: TaskResponse) -> str:
        # Add parent class enhancements (throughput info)
        response = super().enhance_response_with_task_output(response, task_response)
        
        # Add time budget information
        time_remaining = task_response.meta.get("time_remaining", 0)
        elapsed_time = task_response.meta.get("elapsed_compute_time", 0)
        time_budget_exhausted = task_response.meta.get("time_budget_exhausted", False)
        
        if time_budget_exhausted:
            response += f"\n\n⏰ TIME BUDGET EXHAUSTED! You used {elapsed_time:.1f}s of your {self.time_limit_seconds}s budget."
        else:
            response += f"\n\n⏳ Time remaining: {int(time_remaining)}s (used: {elapsed_time:.1f}s/{self.time_limit_seconds}s)"
            response += f"\n💡 Consider your time budget when planning your next actions!"
        
        return response
    
    def _to_dict(self) -> Dict[str, Any]:
        base_dict = super()._to_dict()
        base_dict.update({
            "time_limit_seconds": self.time_limit_seconds,
            "elapsed_compute_time": self.elapsed_compute_time
        })
        return base_dict