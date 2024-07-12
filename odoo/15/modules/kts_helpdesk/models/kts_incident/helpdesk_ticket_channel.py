from odoo import fields, models


class HelpdeskTicketChannel(models.Model):

    _name = "helpdesk.ticket.channel"
    _description = "Helpdesk Ticket Channel"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

class CancelEmailTemplate(models.Model):
    _name = "email.template"
    _description = "Cancel Email"
    name = fields.Char(string="Name")
