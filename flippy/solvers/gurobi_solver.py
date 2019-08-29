from typing import Optional
import gurobipy
from flippy.lp_problem import LpProblem
from flippy.lp_variable import VarType
from flippy.lp_objective import Maximize
from flippy.solvers.base_solver import SolutionStatus


STATUS_MAPPING = {
    gurobipy.GRB.OPTIMAL: SolutionStatus.Optimal,
    gurobipy.GRB.INFEASIBLE: SolutionStatus.Infeasible,
    gurobipy.GRB.INF_OR_UNBD: SolutionStatus.Infeasible,
    gurobipy.GRB.UNBOUNDED: SolutionStatus.Unbounded,
    gurobipy.GRB.ITERATION_LIMIT: SolutionStatus.NotSolved,
    gurobipy.GRB.NODE_LIMIT: SolutionStatus.NotSolved,
    gurobipy.GRB.TIME_LIMIT: SolutionStatus.NotSolved,
    gurobipy.GRB.SOLUTION_LIMIT: SolutionStatus.NotSolved,
    gurobipy.GRB.INTERRUPTED: SolutionStatus.NotSolved,
    gurobipy.GRB.NUMERIC: SolutionStatus.NotSolved
}


class GurobiSolver:
    def __init__(self, mip_gap: float = 0.1, timeout: Optional[int] = None) -> None:
        self.mip_gap = mip_gap
        self.timeout = timeout

    def solve(self, lp_problem: LpProblem) -> SolutionStatus:
        model = gurobipy.Model(lp_problem.name)

        model.setParam('MIPGap', self.mip_gap)
        if self.timeout is not None:
            model.setParam('TimeLimit', self.timeout)

        if lp_problem.lp_objective and lp_problem.lp_objective.sense == Maximize:
            model.setAttr("ModelSense", -1)

        if not isinstance(lp_problem, LpProblem):
            raise Exception('%s is not an LpProblem' % lp_problem)

        if lp_problem.lp_objective.sense == Maximize:
            model.setAttr("ModelSense", -1)

        self.add_variables(lp_problem, model)
        self.add_constraints(lp_problem, model)
        solution_status = self.acutal_solve(model)
        self.retrive_values(lp_problem, model)
        return STATUS_MAPPING[solution_status]

    @staticmethod
    def add_variable(var, obj_coef, model):
        low_bound = var.low_bound
        if low_bound is None:
            low_bound = -gurobipy.GRB.INFINITY
        up_bound = var.up_bound
        if up_bound is None:
            up_bound = gurobipy.GRB.INFINITY
        if var.var_type == VarType.Continuous:
            var_type = gurobipy.GRB.CONTINUOUS
        else:
            var_type = gurobipy.GRB.INTEGER
        var.solver_var = model.addVar(low_bound, up_bound, vtype=var_type, obj=obj_coef, name=var.name)

    def add_variables(self, lp_problem: LpProblem, model: gurobipy.Model) -> None:
        for _, var in lp_problem.lp_variables.items():
            self.add_variable(var, lp_problem.lp_objective.expr.get(var, 0), model)
        model.update()

    def add_constraints(self, lp_problem: LpProblem, model: gurobipy.Model) -> None:
        for name, constraint in lp_problem.lp_constraints.items():
            lhs_expr = [(coef, var.solver_var) for var, coef in constraint.lhs_expression.expr.items()]
            if constraint.slack:
                self.add_variable(constraint.slack_variable,
                                  (-1 if lp_problem.lp_objective.sense == Maximize else 1) * constraint.slack_penalty,
                                  model)
                lhs_expr += [((-1 if constraint.sense == 'leq' else 1), constraint.slack_variable.solver_var)]
            lhs_expr = gurobipy.LinExpr(lhs_expr)
            lhs_expr.addConstant(constraint.lhs_expression.const)
            rhs_expr = gurobipy.LinExpr(
                [(coef, var.solver_var) for var, coef in constraint.rhs_expression.expr.items()])
            rhs_expr.addConstant(constraint.rhs_expression.const)
            if constraint.sense.lower() == 'leq':
                relation = gurobipy.GRB.LESS_EQUAL
            elif constraint.sense.lower() == 'geq':
                relation = gurobipy.GRB.GREATER_EQUAL
            else:
                relation = gurobipy.GRB.EQUAL
            constraint.solver_constraint = model.addConstr(lhs_expr, relation, rhs_expr, name)
        model.update()

    def acutal_solve(self, model: gurobipy.Model) -> int:
        model.optimize()
        return model.Status

    def retrive_values(self, lp_problem: LpProblem, model: gurobipy.Model) -> None:
        try:
            for var, value in zip(lp_problem.lp_variables.values(),
                                  model.getAttr(gurobipy.GRB.Attr.X, model.getVars())):
                var._value = value
        except (gurobipy.GurobiError, AttributeError):
            pass
