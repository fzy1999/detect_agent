from agent.detect_agent.controller import control_loop
from langfuse import Langfuse

class Detect_Agent:
    def __init__(self, agent_prompt, basic_prompt) -> None:

        self.ap = agent_prompt
        self.bp = basic_prompt

    def run(self, instruction, logger, max_step=25, max_turn=5):
            
        logger.info(f"Objective: {instruction}")
        
        # 创建langfuse客户端（已经在run_detect_agent.py中初始化）
        from agent.run_detect_agent import langfuse
        
        # 创建trace
        trace = langfuse.trace(
            name="Detect_Agent",
            input=instruction,
            metadata={
                "agent_prompt": self.ap.rules,
                "background_prompt": self.bp.cand
            }
        )
        
        # 执行控制循环
        prediction, trajectory, prompt = control_loop(
            instruction, 
            "", 
            self.ap, 
            self.bp, 
            logger=logger, 
            max_step=max_step, 
            max_turn=max_turn,
            langfuse_trace=trace  # 传递trace对象
        )
        
        # 更新trace完成状态
        trace.update(
            output=prediction,
            metadata={
                "trajectory_length": len(trajectory)
            }
        )
        
        logger.info(f"Result: {prediction}")

        return prediction, trajectory, prompt,trace.id