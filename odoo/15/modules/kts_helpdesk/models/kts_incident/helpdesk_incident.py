from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError


class SelectedWorkflowLineHelpdeskIncident(models.Model):
    _inherit = "selected.workflow.line"

    helpdesk_incident_id = fields.Many2one(comodel_name="helpdesk.incident")


class HelpdeskIncident(models.Model):
    _name = "helpdesk.incident"
    _description = "Incident Reporting"
    _rec_name = "number"
    _order = "number desc"
    _inherit = ["mail.thread.cc", "mail.activity.mixin","workflow.validation"]

    number = fields.Char(string="Incident number", default="/", readonly=True)
    name = fields.Char(string="Title", required=True)
    description = fields.Html(required=True, sanitize_style=True)
    it_remark = fields.Text(string="IT Remark")

    ticket_attachment_ids = fields.Many2many('ir.attachment', 'ticket_attach_rel', 'doc_id', 'attach_id3', string="Attachment",
                                         help='You can attach the copy of your document')

    channel_id = fields.Many2one(
        comodel_name="helpdesk.ticket.channel",
        string="Channel",
        help="Channel indicates where the source of a ticket"
        "comes from (it could be a phone call, an email...)",
    )
    category_id = fields.Many2one(
        comodel_name="helpdesk.ticket.category",
        string="Category",
    )
    team_id = fields.Many2one(
        related="category_id.team",
        string="Team",
    )
    priority = fields.Selection(
        selection=[
            ("0", _("Very Low")),
            ("1", _("Low")),
            ("2", _("Normal")),
            ("3", _("High")),
            ("4", _("Critical")),
        ],
        string="Priority",
        default="1",
    )
    active = fields.Boolean("Active", default=True)
    workflow_lines = fields.One2many(string="Workflow Lines", comodel_name='selected.workflow.line',
                                     inverse_name='helpdesk_incident_id', copy=True,
                                     help="Workflow line")

    @api.model
    def default_get(self, fields):
        defaults = super(HelpdeskIncident, self).default_get(fields)
        workflow = self.env['workflow.model'].sudo().search([('model_name', '=', 'helpdesk.incident')])
        defaults['workflow_id'] = workflow
        stages = []
        stage_lines = []

        for stage in workflow.stage_ids:
            stages = stages + [stage.id]

        if workflow:
            stage_lines = workflow.get_stage_lines()

        defaults['workflow_lines'] = stage_lines
        defaults['workflow_stage_id'] = stages

        return defaults

    @api.onchange('category_id')
    def _compute_team(self):
        if self.category_id:
            self.team_id = self.category_id.team
            if len(self.workflow_lines) >= 1:
                self.workflow_lines[1].team_id = self.team_id.id
                if self.team_id.team_manager_id.id:
                    self.workflow_lines[1].user_id = self.team_id.team_manager_id.id

                elif self.team_id.team_leader_id.id:
                    self.workflow_lines[1].user_id = self.team_id.team_manager_id.id


    
    @api.model
    def create(self, vals):
        if vals.get("number", "/") == "/":
            vals["number"] = self._prepare_ticket_number(vals)
        res = super().create(vals)
        return res

    def write(self, vals):
        if "active" in vals:
            if self.env.user.has_group('kts_workflow.group_defence_user'):
                raise UserError(_("You can not archive / Unarchive"))
        return super().write(vals)

    def _prepare_ticket_number(self, values):
        seq = self.env["ir.sequence"]
        return seq.next_by_code("helpdesk.ticket.sequence") or "/"

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['number'] = "/"
        return super(HelpdeskIncident, self).copy(default=default)










