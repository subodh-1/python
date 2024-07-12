from odoo import fields, models


class HelpdeskCategory(models.Model):

    _name = "helpdesk.ticket.category"
    _description = "Helpdesk Ticket Category"
    _order = "name"

    active = fields.Boolean(
        string="Active",
        default=True,
    )
    name = fields.Char(
        string="Name",
        required=True,
    )

    team = fields.Many2one(
        comodel_name="workflow.team",
        string="Team",
        required=True,
    )
