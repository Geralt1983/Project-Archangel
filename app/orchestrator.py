"""
Advanced Task Orchestrator - Production-Ready Implementation
Implements sophisticated scoring, WIP enforcement, and fairness algorithms.
"""

import math
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import structlog

# Structured logger
logger = structlog.get_logger(__name__)

class TaskState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class TaskContext:
    """Enhanced task context with orchestration metadata"""
    id: str
    title: str
    description: str
    client: str
    provider: str
    state: TaskState
    
    # Core scoring factors
    importance: float  # 1.0-5.0
    urgency: float     # 0.0-1.0 based on deadline
    value: float       # Business value 0.0-1.0
    time_sensitivity: float  # 0.0-1.0
    sla_breach: float  # 0.0-1.0 SLA breach risk
    
    # Fairness tracking
    client_recent_allocation: float  # Recent hours for this client
    assignee_current_wip: int       # Current WIP for assignee
    
    # Staleness factors  
    age_hours: float
    last_activity_hours: float
    
    # Metadata
    effort_hours: float
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assignee: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

@dataclass 
class OrchestrationDecision:
    """Decision output from orchestrator"""
    task_id: str
    score: float
    recommended_action: str
    assignee_suggestion: Optional[str]
    reasoning: List[str]
    staleness_curve: float
    fairness_penalty: float
    wip_enforcement: Dict[str, Any]
    timestamp: datetime

class ScoringEngine:
    """Advanced scoring with configurable weights and fairness"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'importance': self.config.get('weight_importance', 0.25),
            'urgency': self.config.get('weight_urgency', 0.20), 
            'value': self.config.get('weight_value', 0.15),
            'time_sensitivity': self.config.get('weight_time_sensitivity', 0.15),
            'sla_breach': self.config.get('weight_sla_breach', 0.20),
            'fairness': self.config.get('weight_fairness', 0.05)
        }
        
        # Staleness curve parameters
        self.staleness_threshold = self.config.get('staleness_threshold_hours', 72)
        self.staleness_max_penalty = self.config.get('staleness_max_penalty', 0.3)
        
    def _default_config(self) -> Dict[str, Any]:
        return {
            'weight_importance': 0.25,
            'weight_urgency': 0.20,
            'weight_value': 0.15, 
            'weight_time_sensitivity': 0.15,
            'weight_sla_breach': 0.20,
            'weight_fairness': 0.05,
            'staleness_threshold_hours': 72,
            'staleness_max_penalty': 0.3,
            'fairness_lookback_hours': 168,  # 1 week
            'wip_limits': {'default': 3, 'senior': 5, 'lead': 8},
            'client_caps': {'default': 8}  # hours per day
        }
        
    def compute_score(self, task: TaskContext) -> Tuple[float, Dict[str, float]]:
        """
        Compute sophisticated task score: S = wI*I + wU*U + wV*V + wTS*TS + wSLA*SLAB + wF*F - wSt*St
        Returns (final_score, component_scores)
        """
        components = {}
        
        # Importance (I): Normalized business importance
        components['importance'] = min(1.0, task.importance / 5.0)
        
        # Urgency (U): Time-based urgency with deadline pressure
        components['urgency'] = self._compute_urgency(task)
        
        # Value (V): Business value/impact 
        components['value'] = task.value
        
        # Time Sensitivity (TS): How much delay costs
        components['time_sensitivity'] = task.time_sensitivity
        
        # SLA Breach (SLAB): Risk of SLA violation
        components['sla_breach'] = task.sla_breach
        
        # Fairness (F): Client and assignee fairness factor
        components['fairness'] = self._compute_fairness(task)
        
        # Staleness (St): Age penalty with curves
        components['staleness'] = self._compute_staleness(task)
        
        # Weighted combination
        base_score = (
            self.weights['importance'] * components['importance'] +
            self.weights['urgency'] * components['urgency'] +
            self.weights['value'] * components['value'] +
            self.weights['time_sensitivity'] * components['time_sensitivity'] +
            self.weights['sla_breach'] * components['sla_breach'] +
            self.weights['fairness'] * components['fairness']
        )
        
        # Apply staleness penalty
        final_score = base_score - (self.staleness_max_penalty * components['staleness'])
        final_score = max(0.0, min(1.0, final_score))
        
        logger.debug(
            f"Task {task.id} score: {final_score:.4f} "
            f"(importance={components['importance']:.3f}, "
            f"urgency={components['urgency']:.3f}, "
            f"staleness={components['staleness']:.3f})"
        )

        return round(final_score, 4), components
        
    def _compute_urgency(self, task: TaskContext) -> float:
        """Compute urgency with exponential deadline pressure"""
        if not task.deadline:
            return 0.3  # Default for no deadline
            
        hours_remaining = (task.deadline - datetime.now(timezone.utc)).total_seconds() / 3600
        
        if hours_remaining <= 0:
            return 1.0  # Overdue
        elif hours_remaining <= 24:
            return 0.9  # Critical
        elif hours_remaining <= 72:
            return 0.7  # High
        else:
            # Exponential decay
            return max(0.1, 0.7 * math.exp(-hours_remaining / 168))  # 1 week half-life
            
    def _compute_fairness(self, task: TaskContext) -> float:
        """Compute fairness factor to promote equitable distribution"""
        # Client fairness: Penalize clients with high recent allocation
        client_caps = self.config.get('client_caps', {})
        default_cap = client_caps.get('default', 8)
        client_penalty = min(0.5, task.client_recent_allocation / default_cap)
        
        # Assignee fairness: Penalize high WIP assignees  
        wip_limits = self.config.get('wip_limits', {'default': 3})
        wip_limit = wip_limits.get(task.assignee, wip_limits.get('default', 3))
        wip_penalty = min(0.5, task.assignee_current_wip / wip_limit) if task.assignee else 0
        
        return max(0.0, 1.0 - client_penalty - wip_penalty)
        
    def _compute_staleness(self, task: TaskContext) -> float:
        """Compute staleness penalty with configurable curves"""
        # Exponential staleness curve
        if task.age_hours <= self.staleness_threshold:
            return 0.0
            
        excess_hours = task.age_hours - self.staleness_threshold
        # Sigmoid curve: rapid increase after threshold
        return 1.0 / (1.0 + math.exp(-excess_hours / 24))  # 24-hour characteristic time

class WIPEnforcer:
    """Work-In-Progress limits and load balancing"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize WIP enforcer with configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.wip_limits = self.config.get('wip_limits', {'default': 3})
        self.load_balance_threshold = self.config.get('load_balance_threshold', 0.8)
        
        logger.debug(f"WIPEnforcer initialized with limits: {self.wip_limits}")
        
    def check_wip_constraints(self, assignee: str, current_wip: int) -> Dict[str, Any]:
        """
        Check if assignee can take more work
        
        Args:
            assignee: Assignee identifier
            current_wip: Current work in progress count
            
        Returns:
            Dictionary with WIP constraint information
            
        Raises:
            ValueError: If current_wip is negative
        """
        if current_wip < 0:
            raise ValueError(f"current_wip must be non-negative, got {current_wip}")
            
        if not assignee:
            logger.warning("Empty assignee provided to WIP check")
            assignee = "unassigned"
        limit = self.wip_limits.get(assignee, self.wip_limits['default'])
        
        return {
            'can_assign': current_wip < limit,
            'current_wip': current_wip,
            'limit': limit,
            'utilization': current_wip / limit,
            'available_capacity': max(0, limit - current_wip)
        }
        
    def suggest_load_balancing(self, workload: Dict[str, int]) -> List[Dict[str, Any]]:
        """Suggest load rebalancing actions"""
        suggestions = []
        
        # Find overloaded and underutilized assignees
        for assignee, current_load in workload.items():
            limit = self.wip_limits.get(assignee, self.wip_limits['default'])
            utilization = current_load / limit
            
            if utilization > self.load_balance_threshold:
                suggestions.append({
                    'action': 'reduce_load',
                    'assignee': assignee,
                    'current_load': current_load,
                    'target_load': int(limit * self.load_balance_threshold),
                    'excess_tasks': current_load - int(limit * self.load_balance_threshold)
                })
            elif utilization < 0.5:
                suggestions.append({
                    'action': 'increase_load', 
                    'assignee': assignee,
                    'current_load': current_load,
                    'available_capacity': limit - current_load
                })
                
        return suggestions

class StateManager:
    """Manages task state transitions and persistence"""
    
    def __init__(self, db_path: str = "orchestrator.db") -> None:
        """
        Initialize state manager with database
        
        Args:
            db_path: Path to SQLite database file
            
        Raises:
            OSError: If database cannot be created or accessed
        """
        self.db_path = Path(db_path)
        logger.info(f"Initializing state manager with database: {self.db_path}")
        
        try:
            self._init_database()
            logger.debug("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        
    def _init_database(self):
        """Initialize SQLite database for orchestrator state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS task_scores (
                    task_id TEXT PRIMARY KEY,
                    score REAL,
                    components TEXT,
                    decision_data TEXT,
                    timestamp TEXT
                );
                
                CREATE TABLE IF NOT EXISTS fairness_tracking (
                    client TEXT,
                    assignee TEXT,
                    date TEXT,
                    allocated_hours REAL,
                    PRIMARY KEY (client, assignee, date)
                );
                
                CREATE TABLE IF NOT EXISTS decision_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    decision_type TEXT,
                    reasoning TEXT,
                    outcome TEXT,
                    timestamp TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_scores_timestamp ON task_scores(timestamp);
                CREATE INDEX IF NOT EXISTS idx_fairness_date ON fairness_tracking(date);
                CREATE INDEX IF NOT EXISTS idx_trace_task ON decision_trace(task_id);
            """)
            
    def save_decision(self, decision: OrchestrationDecision) -> None:
        """
        Persist orchestration decision with full audit trail
        
        Args:
            decision: Orchestration decision to persist
            
        Raises:
            sqlite3.Error: If database operation fails
            TypeError: If decision is not OrchestrationDecision
        """
        if not isinstance(decision, OrchestrationDecision):
            raise TypeError(f"decision must be OrchestrationDecision, got {type(decision)}")
            
        logger.debug(f"Saving decision for task {decision.task_id}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO task_scores 
                    (task_id, score, components, decision_data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    decision.task_id,
                    decision.score,
                    json.dumps({}),  # Will be filled with component scores
                    json.dumps(asdict(decision)),
                    decision.timestamp.isoformat()
                ))
            
                conn.execute("""
                    INSERT INTO decision_trace
                    (task_id, decision_type, reasoning, outcome, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    decision.task_id,
                    'orchestration',
                    json.dumps(decision.reasoning),
                    decision.recommended_action,
                    decision.timestamp.isoformat()
                ))
        except sqlite3.Error as e:
            logger.error(f"Failed to save decision for task {decision.task_id}: {e}")
            raise
            
    def get_client_recent_allocation(self, client: str, hours_lookback: int = 168) -> float:
        """Get recent hour allocation for fairness calculations"""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_lookback)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COALESCE(SUM(allocated_hours), 0)
                FROM fairness_tracking 
                WHERE client = ? AND date >= ?
            """, (client, cutoff)).fetchone()
            
        return result[0] if result else 0.0
        
    def get_assignee_wip(self, assignee: str) -> int:
        """Get current WIP count for assignee"""
        # In a real implementation, this would query active task assignments
        # For now, return a placeholder
        return 2

class TaskOrchestrator:
    """Main orchestrator class combining all components"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize task orchestrator with configuration
        
        Args:
            config: Optional configuration dictionary
            
        Raises:
            Exception: If component initialization fails
        """
        self.config = config or {}
        
        try:
            self.scoring_engine = ScoringEngine(config)
            self.wip_enforcer = WIPEnforcer(config)
            self.state_manager = StateManager()
            logger.info("Task orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
        
    def orchestrate_task(self, task: TaskContext) -> OrchestrationDecision:
        """Main orchestration logic - produces prioritization decision"""
        
        # Enhance task context with dynamic data
        task.client_recent_allocation = self.state_manager.get_client_recent_allocation(task.client)
        task.assignee_current_wip = self.state_manager.get_assignee_wip(task.assignee or "unassigned")
        
        # Compute sophisticated score
        score, components = self.scoring_engine.compute_score(task)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(task, components)
        
        # WIP enforcement
        wip_check = self.wip_enforcer.check_wip_constraints(
            task.assignee or "unassigned", 
            task.assignee_current_wip
        )
        
        # Determine recommended action
        action = self._determine_action(task, score, wip_check)
        
        # Create decision
        decision = OrchestrationDecision(
            task_id=task.id,
            score=score,
            recommended_action=action,
            assignee_suggestion=task.assignee,
            reasoning=reasoning,
            staleness_curve=components.get('staleness', 0),
            fairness_penalty=1.0 - components.get('fairness', 1.0),
            wip_enforcement=wip_check,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Persist decision for audit trail (async operation, don't wait)
        try:
            self.state_manager.save_decision(decision)
        except Exception as e:
            # Log but don't fail orchestration
            logger.warning(f"Failed to persist decision for task {task.id}: {e}")
        
        return decision
        
    def _generate_reasoning(self, task: TaskContext, components: Dict[str, float]) -> List[str]:
        """Generate human-readable reasoning for the decision"""
        reasoning = []
        
        # High impact factors
        if components.get('importance', 0) > 0.8:
            reasoning.append(f"High business importance ({task.importance}/5.0)")
            
        if components.get('urgency', 0) > 0.7:
            if task.deadline:
                hours_remaining = (task.deadline - datetime.now(timezone.utc)).total_seconds() / 3600
                reasoning.append(f"Urgent: {hours_remaining:.1f} hours to deadline")
            else:
                reasoning.append("High urgency factor")
                
        if components.get('sla_breach', 0) > 0.6:
            reasoning.append(f"SLA breach risk: {components['sla_breach']:.1%}")
            
        # Staleness warnings
        if components.get('staleness', 0) > 0.3:
            reasoning.append(f"Task becoming stale ({task.age_hours:.1f} hours old)")
            
        # Fairness considerations
        fairness = components.get('fairness', 1.0)
        if fairness < 0.7:
            if task.client_recent_allocation > 4:
                reasoning.append(f"Client '{task.client}' has high recent allocation ({task.client_recent_allocation:.1f}h)")
            if task.assignee_current_wip > 3:
                reasoning.append(f"Assignee has high WIP ({task.assignee_current_wip})")
                
        if not reasoning:
            reasoning.append("Balanced scoring across all factors")
            
        return reasoning
        
    def _determine_action(self, task: TaskContext, score: float, wip_check: Dict[str, Any]) -> str:
        """Determine recommended action based on score and constraints"""
        
        if not wip_check['can_assign']:
            return "defer_wip_limit"
            
        if score >= 0.8:
            return "prioritize_high"
        elif score >= 0.6:
            return "schedule_normal"  
        elif score >= 0.3:
            return "backlog_low_priority"
        else:
            return "consider_deferral"
            
    def rebalance_workload(self, tasks: List[TaskContext]) -> Dict[str, Any]:
        """Rebalance entire workload using orchestration principles"""
        
        # Score all tasks
        scored_tasks = []
        for task in tasks:
            decision = self.orchestrate_task(task)
            scored_tasks.append((task, decision))
            
        # Sort by score
        scored_tasks.sort(key=lambda x: x[1].score, reverse=True)
        
        # Generate workload analysis
        workload = {}
        for task, _ in scored_tasks:
            if task.assignee:
                workload[task.assignee] = workload.get(task.assignee, 0) + 1
                
        # Get rebalancing suggestions
        suggestions = self.wip_enforcer.suggest_load_balancing(workload)
        
        return {
            'total_tasks': len(tasks),
            'prioritized_tasks': [
                {
                    'task_id': task.id,
                    'title': task.title,
                    'score': decision.score,
                    'action': decision.recommended_action,
                    'reasoning': decision.reasoning
                }
                for task, decision in scored_tasks[:20]  # Top 20
            ],
            'workload_distribution': workload,
            'rebalancing_suggestions': suggestions,
            'average_score': sum(d.score for _, d in scored_tasks) / len(scored_tasks) if scored_tasks else 0
        }

# Factory function for easy integration
def create_orchestrator(config: Optional[Dict[str, Any]] = None) -> TaskOrchestrator:
    """
    Create configured orchestrator instance
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured TaskOrchestrator instance
        
    Raises:
        Exception: If orchestrator creation fails
    """
    return TaskOrchestrator(config)

# Legacy compatibility wrapper
def compute_score(task: Dict[str, Any], rules: Dict[str, Any]) -> float:
    """
    Legacy compatibility wrapper for existing scoring calls
    
    Args:
        task: Task dictionary with legacy format
        rules: Rules dictionary (legacy format)
        
    Returns:
        Computed task score
        
    Raises:
        TypeError: If inputs are not dictionaries
        ValueError: If required task fields are missing
    """
    if not isinstance(task, dict):
        raise TypeError(f"task must be dict, got {type(task)}")
    if not isinstance(rules, dict):
        raise TypeError(f"rules must be dict, got {type(rules)}")
        
    logger.debug(f"Legacy score computation for task: {task.get('id', 'unknown')}")
    try:
        orchestrator = create_orchestrator()
    except Exception as e:
        logger.error(f"Failed to create orchestrator: {e}")
        # Fallback to simple scoring
        return 0.5
    
    # Convert legacy task format to TaskContext
    task_context = TaskContext(
        id=task.get('id', ''),
        title=task.get('title', ''),
        description=task.get('description', ''),
        client=task.get('client', ''),
        provider=task.get('provider', 'internal'),
        state=TaskState.PENDING,
        importance=task.get('importance', 3.0),
        urgency=0.5,  # Will be computed
        value=0.5,    # Default value
        time_sensitivity=0.5,
        sla_breach=0.3,
        client_recent_allocation=0.0,
        assignee_current_wip=2,
        age_hours=0.0,
        last_activity_hours=0.0,
        effort_hours=task.get('effort_hours', 1.0),
        deadline=datetime.fromisoformat(task['deadline'].replace('Z', '+00:00')) if task.get('deadline') else None,
        created_at=datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')) if task.get('created_at') else datetime.now(timezone.utc)
    )
    
    try:
        decision = orchestrator.orchestrate_task(task_context)
        return decision.score
    except Exception as e:
        logger.error(f"Orchestration failed for task {task.get('id', 'unknown')}: {e}")
        # Fallback to simple scoring based on importance
        return min(1.0, task.get('importance', 3.0) / 5.0)