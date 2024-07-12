from odoo import api, fields, models
from odoo.osv import expression


class SelectedWorkflowLine(models.Model):
    _name = "selected.workflow.line"
    _description = "Selected Workflow Lines"
    _order = "sequence"
    _inherit = ['mail.thread']

    team_id = fields.Many2one(comodel_name="workflow.team", string='Team')
    user_id = fields.Many2one(comodel_name="res.users", string='Responsible', tracking=False)
    is_user = fields.Boolean(related="stage_id.is_user", readonly=True)
    stage_id = fields.Many2one(comodel_name="workflow.stage", string='Workflow Stage')
    mail_template_id = fields.Many2one(
        related="stage_id.mail_template_id",
        help="If set an email will be sent to the "
             "concerned when the workflow"
             "reaches this step.",
    )
    sequence = fields.Integer(related="stage_id.sequence", readonly=False)
    is_team = fields.Boolean(related="stage_id.is_team", readonly=True)
    is_final = fields.Boolean(related="stage_id.is_final")
    is_cancel = fields.Boolean(related="stage_id.is_cancel")
    create_date = fields.Date(string='Date')
    start_date = fields.Datetime(string='Start Date', readonly=True, copy=False,)
    valid_until = fields.Datetime(string='Valid Until', readonly=True, copy=False,)
    note = fields.Text(string='Note', copy=False)
    notify_users = fields.Selection(
        [('responsible', 'Stage Responsible'), ('all', 'All')],
        default='responsible', copy=False, string="Notify Users")

    workflow_id = fields.Many2one(
        comodel_name="workflow.model",
        string="Workflow"
    )


SelectedWorkflowLine()


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if self.env.context.get('team_id', False):
            team = self.env['workflow.team'].browse(self.env.context['team_id'])
            if team:
                ids = team.user_ids.ids;
                if team.team_manager_id:
                    ids.append(team.team_manager_id.id)
                if team.team_leader_id:
                    ids.append(team.team_leader_id.id)
                domain = [("id", "in", ids), ('name', operator, name)]
                return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super(ResUsers, self)._name_search(name, args=args, operator=operator, limit=limit,
                                                       name_get_uid=name_get_uid)


class WorkflowModel(models.Model):
    _name = "workflow.model"
    _description = "Workflow Model"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    description = fields.Html(translate=True, sanitize_style=True)
    active = fields.Boolean(default=True)
    stage_ids = fields.Many2many('workflow.stage', string='Workflow Stages', required=True)
    model_name = fields.Many2one('ir.model', string="Model Name", required=True, ondelete='cascade')

    def get_stage_lines(self):
        stage_lines = []

        for stage in self.stage_ids:
            stage_lines = stage_lines + [[0, 0, {'stage_id': stage.id, 'user_id': stage.user_id.id,
                                                 'notify_users': stage.notify_users, 'note': '',
                                                 'sequence': stage.sequence, 'is_team': stage.is_team,
                                                 'team_id': stage.team_id, 'is_final': stage.is_final,
                                                 'is_cancel': stage.is_cancel, 'is_user': stage.is_user}]]
        return stage_lines


class WorkflowStage(models.Model):
    _name = "workflow.stage"
    _description = "Workflow Stage"
    _order = "sequence, id"

    name = fields.Char(string="Stage Name", required=True, translate=True)
    description = fields.Char(string="Description")
    sequence = fields.Integer(default=1)
    active = fields.Boolean(default=True)
    is_final = fields.Boolean(string="Is Final Stage", default=False)
    is_cancel = fields.Boolean(string="Is Cancel Stage", default=False)
    is_team = fields.Boolean(string="Is Team Responsible", default=False)
    team_id = fields.Many2one(comodel_name="workflow.team", string='Team')
    notify_users = fields.Selection(
        [('responsible', 'Stage Responsible'), ('all', 'All')],
        default='responsible', copy=False, string="Notify Users")
    user_id = fields.Many2one(comodel_name="res.users", string='Responsible')
    sub_stage = fields.Boolean(default=False, string="Sub-Stage", help="This stage can be used for sub stage workflow too." )
    optional_stage=fields.Boolean(default=False, string="Optional Stage",  help="This Stage can be skipped during workflow execution.")
    system_stage=fields.Boolean(default=False, string="System Stage")
    start_stage=fields.Boolean(default=False, string="Start Stage")
    is_user = fields.Boolean(default=False, compute='_compute_visible_to_user')

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain=[],
        help="If set an email will be sent to the "
             "concerned when the workflow"
             "reaches this step.",
    )


    fold = fields.Boolean(
        string="Folded in Kanban",
        help="This stage is folded in the kanban view "
        "when there are no records in that stage "
        "to display.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.onchange('is_team', 'team_id')
    def _compute_is_team(self):
        if self.is_team:
            self.user_id = None
            if self.team_id.team_manager_id.id:
                self.user_id = self.team_id.team_manager_id.id

            elif self.team_id.team_leader_id.id:
                self.user_id = self.team_id.team_manager_id.id
        else:
            self.is_team = None

    @api.depends('team_id')
    def _compute_visible_to_user(self):
        for record in self:
            record.is_user = True
            if record.is_team:
                record.is_user = False
                if record.team_id.team_manager_id.id and (record.team_id.team_manager_id.id == self._uid):
                    record.is_user = True
                elif record.team_id.team_leader_id.id and (record.team_id.team_leader_id.id == self._uid):
                    record.is_user = True
                elif self.env.user.has_group('kts_workflow.group_defence_admin'):
                    record.is_user = True

    def _get_left_right_stages(self, stage, stages):
        stages = sorted(stages, key=lambda x: x.sequence)
        loc = stages.index(stage)
        allowed_stages=[]

        for x in range(loc, len(stages)):
            if stages[x]==stage:
                continue

            if stages[x].optional_stage:
                allowed_stages=allowed_stages+[stages[x]]
                continue

            allowed_stages=allowed_stages+[stages[x]]
            break

        for x in range(loc, -1,-1):
            if stages[x]==stage:
                continue

            if stages[x].optional_stage:
                allowed_stages=allowed_stages+[stages[x]]
                continue
            allowed_stages=allowed_stages+[stages[x]]
            break
        return allowed_stages

    def _get_sorted_stages(self, stages):
       return sorted(stages, key=lambda x: x.sequence)

    def get_system_stages(self):
        return self.search([('system_stage','=',True)])

    @api.model
    def default_get(self, fields):
        result = super(WorkflowStage, self).default_get(fields)
        return result

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        workflow_id = self.env.context.get('workflow_id')
        if workflow_id:
            workflow_id = self.env['workflow.model'].browse(workflow_id)
            return  workflow_id.stage_ids
        sub_stage = self.env.context.get('sub_stage')
        if sub_stage:
            args=args+[('sub_stage','=',True)]

        return super(WorkflowStage, self).search( args, offset, limit, order, count)


class ResCompany(models.Model):
    _inherit = "res.company"
    email_name = fields.Char("Email Title")
