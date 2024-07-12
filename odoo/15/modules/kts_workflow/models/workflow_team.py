from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class WorkflowTeam(models.Model):

    _name = "workflow.team"
    _description = "workflow Ticket Team"

    name = fields.Char(string="Name", required=True)
    user_ids = fields.Many2many(comodel_name="res.users", string="Members")
    active = fields.Boolean(default=True)

    team_manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Team Manager",
    )

    team_leader_id = fields.Many2one(
        comodel_name="res.users",
        string="Team Leader",
    )

    color = fields.Integer(string="Color Index", default=0)