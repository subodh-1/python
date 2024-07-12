from odoo import api, fields, models, _
from odoo.exceptions import UserError
from lxml import etree


class WorkflowValidation(models.Model):
    _name = "workflow.validation"
    _inherit = ['mail.thread']
    _description = "Common Workflow Validation"

    def _get_default_stage_id(self):
        self.env.context = dict(self.env.context)
        self.env.context.update({'workflow_id': self.workflow_id.id or False})
        return self.env["workflow.stage"].search([], limit=1)[0]

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        self.env.context = dict(self.env.context)
        self.env.context.update({'workflow_id': self.workflow_id.id or False})
        stage_ids = self.env["workflow.stage"].search([])
        return stage_ids

    workflow_id = fields.Many2one(
        comodel_name="workflow.model",
        string="Workflow"
    )

    workflow_stage_id = fields.Many2one('workflow.stage', string='Workflow Stage',
                                        compute='_compute_stage_id',
                                        store=True, readonly=False, ondelete='restrict',
                                        tracking=True, index=True,
                                        group_expand='_read_group_stage_ids',
                                        copy=False)
    current_status = fields.Char(string="Status", related="workflow_stage_id.name", store=True)

    stage_sequence = fields.Integer(related="workflow_stage_id.sequence", readonly=False)

    responsible_user = fields.Many2one("res.users", string="Stage Responsible")
    close_date = fields.Date(string="Close Date")
    close_by = fields.Many2one("res.users", string="Close By", readonly=True)
    website_url = fields.Char()
    approval_name = fields.Char()

    def _work_flow_access_validation(self):
        if not self.workflow_id or not self.workflow_lines or not self.workflow_id:
            return

        if self.workflow_stage_id.is_final:
            msg = "Can not edit a record, It's already Close. "
            raise UserError(msg)

        msg = "You are not responsible change current state of this record."

        for line in self.workflow_lines:

            if line.stage_id.id == self.workflow_stage_id.id:
                if line.user_id.id and (line.user_id.id != self._uid):
                    if line.is_team and (
                            (line.team_id.team_manager_id.id and (line.team_id.team_manager_id.id == self._uid)) or
                            (line.team_id.team_leader_id.id and (line.team_id.team_leader_id.id == self._uid))
                    ):
                        return
                    elif line.team_id.user_ids:
                        ids = [x.id for x in line.team_id.user_ids]
                        if self._uid in ids:
                            return
                    raise UserError(msg)

                if not line.user_id.id and line.is_team:
                    if line.team_id.team_manager_id.id and (line.team_id.team_manager_id.id == self._uid):
                        return
                    elif line.team_id.team_leader_id.id and (line.team_id.team_leader_id.id == self._uid):
                        return
                    elif line.team_id.user_ids:
                        ids = [x.id for x in line.team_id.user_ids]
                        if self._uid in ids:
                            return
                        raise UserError(msg)
                    elif self.env.user.has_group('kts_workflow.group_defence_admin'):
                        return
                    else:
                        raise UserError(msg)

    def _check_if_stage_valid(self, record, workflow_stage_id):
        for line in record.workflow_lines:
            if line.stage_id.id == workflow_stage_id:
                return True
        return False

    @api.model
    def on_cick_statusbar_stage(self, record, workflow_stage_id):
        if not workflow_stage_id:
            return True

        r = self.browse(record['id'])
        r._work_flow_access_validation()

        if not self._check_if_stage_valid(r, workflow_stage_id):
            raise UserError(
                _(" '%s' state is not yet configured in workflow.", self.workflow_stage_id.name))
        allowed_stages = self.env['workflow.stage']._get_left_right_stages(
            r.workflow_stage_id, r.workflow_id.stage_ids)

        stage = self.env['workflow.stage'].browse(workflow_stage_id)
        if stage.is_final and stage.is_cancel:
            return

        if stage not in allowed_stages:
            names = [x.name for x in allowed_stages]
            raise UserError(_("You can change state to following stages only: %s", str(names)))
        message = "You may not be able to edit record. Would you like to change current state?"
        return message

    @api.model
    def create(self, vals):
        if vals.get("workflow_id"):
            workflow = self.env['workflow.model'].browse(vals.get("workflow_id"))
            stage_ids = [x.id for x in workflow.stage_ids]
            vals['workflow_stage_id'] = stage_ids[0]
            for val in vals.get('workflow_lines'):
                if val[2].get('stage_id') == stage_ids[0]:
                    val[2]['start_date'] = fields.Datetime.now()
                    break

        result = super(WorkflowValidation, self).create(vals)
        return result

    def write(self, vals):
        if "active" in vals:
            if self.env.user.has_group('kts_workflow.group_defence_admin'):
                return super().write(vals)

        for record in self:
            record._work_flow_access_validation()

            if vals.get("workflow_stage_id"):
                workflow_stage = record.env['workflow.stage'].browse(vals.get("workflow_stage_id"))
                if workflow_stage.is_final:
                    vals['close_date'] = fields.Date.today()
                    vals['close_by'] = record.env.uid
                    vals['responsible_user'] = record.env.uid

                for line in record.workflow_lines:
                    if line.stage_id.id == vals.get("workflow_stage_id"):
                        line.write({'start_date': fields.Datetime.now()})

                        email_to = ''
                        email_cc = ''
                        self.approval_name = ''
                        self.website_url = ''

                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                        self.website_url = base_url

                        if line.mail_template_id:
                            if line.is_team:
                                if line.team_id.team_manager_id:
                                    employee_ids = self.env['hr.employee'].sudo().search(
                                        [('user_id', '=', line.team_id.team_manager_id.id)])
                                    for employee in employee_ids:
                                        email_to = employee.sdc_email

                                if line.team_id.team_leader_id:
                                    employee_ids = self.env['hr.employee'].sudo().search(
                                        [('user_id', '=', line.team_id.team_leader_id.id)])
                                    for employee in employee_ids:
                                        email_to += ',' + employee.sdc_email

                                if self._name == 'helpdesk.dt' and line.user_id.id:
                                    employee_ids = self.env['hr.employee'].sudo().search(
                                        [('user_id', '=', line.user_id.id)])
                                    for employee in employee_ids:
                                        email_to = employee.sdc_email
                                        self.approval_name = employee.name

                                if line.team_id.user_ids and not self._name == 'helpdesk.dt':
                                    employee_ids = self.env['hr.employee'].sudo().search(
                                        [('user_id', 'in', line.team_id.user_ids.ids)])
                                    for employee in employee_ids:
                                        email_cc += employee.sdc_email + ','
                            else:
                                if line.user_id:
                                    employee_ids = self.env['hr.employee'].sudo().search(
                                        [('user_id', '=', line.user_id.id)])
                                    for employee in employee_ids:
                                        email_to = employee.sdc_email
                                        self.approval_name = employee.name

                            template_values = {
                                'email_to': email_to,
                                'email_cc': email_cc,
                                'auto_delete': False,
                            }

                            line.mail_template_id.write(template_values)
                            line.mail_template_id.send_mail(self.id, force_send=True)

                        else:
                            if line.stage_id.is_final and not line.stage_id.is_cancel:
                                if self._name == 'helpdesk.incident':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Incident Reporting: Submitted to Close')], limit=1)
                                elif self._name == 'helpdesk.ftp':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'FTP Data Transfer: Submitted to Close')], limit=1)
                                elif self._name == 'helpdesk.cd':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'CD/DVD Request: Write Pending To Close')], limit=1)
                                elif self._name == 'site.package':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Site Package: Submitted to Close')], limit=1)
                                elif self._name == 'asset.request':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'PC Request: Allocation To Close')], limit=1)
                                elif self._name == 'asset.transfer':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Asset Transfer: Allocation To Close')], limit=1)
                                elif self._name == 'asset.tracking':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Asset Request: Returned To Close')], limit=1)
                                elif self._name == 'stationary.request':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Stationary Request: Submitted to Close')], limit=1)
                                elif self._name == 'helpdesk.dt':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Helpdesk Data Transfer: Submitted to Close')], limit=1)
                                elif self._name == 'library.tracking':
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'Library Book Request: Returned To Close')], limit=1)
                                else:
                                    template = self.env['mail.template'].sudo().search(
                                        [('name', '=', 'No Template assign')], limit=1)

                                if template.id:
                                    template_id = self.env['mail.template'].browse(template.id)
                                    if template_id:
                                        employee_ids = self.env['hr.employee'].sudo().search(
                                            [('user_id', '=', self.create_uid.id)])
                                        for employee in employee_ids:
                                            email_to = employee.sdc_email

                                        template_values = {
                                            'email_to': email_to,
                                            'email_cc': email_cc,
                                            'auto_delete': False,
                                        }

                                        template_id.write(template_values)
                                        template_id.send_mail(self.id, force_send=True)
                            elif line.stage_id.is_final and line.stage_id.is_cancel:
                                self._send_cancel_mail()

                        if line.user_id:
                            vals['responsible_user'] = line.user_id
                        break

                stage_ids = [x.id for x in record.workflow_id.stage_ids]
                for line in record.workflow_lines:
                    index = stage_ids.index(vals.get("workflow_stage_id"))
                    if index > 0 and line.stage_id.id == stage_ids[index - 1]:
                        line.write({'valid_until': fields.Datetime.now()})
                        break

            if vals.get("workflow_id"):
                workflow = record.env['workflow.model'].browse(vals.get("workflow_id"))
                stage_ids = [x.id for x in workflow.stage_ids]
                vals['workflow_stage_id'] = stage_ids[0]

        obj = super().write(vals)
        if vals.get("workflow_lines"):
            for request in self:
                for workflow_line in request.workflow_lines:
                    if workflow_line.stage_id.id == request.workflow_stage_id.id:
                        request.write({'responsible_user': workflow_line.user_id})
                        break
        return obj

    def _send_cancel_mail(self):

        email_to = ''
        email_cc = ''
        template = self.env['mail.template'].sudo().search(
            [('name', '=', 'Cancel: Request')], limit=1)
        if template.id:
            template_id = self.env['mail.template'].browse(template.id)

            employee_ids = self.env['hr.employee'].sudo().search(
                [('user_id', '=', self.create_uid.id)])
            for employee in employee_ids:
                email_to = employee.sdc_email

            subject = 'Your Request Is Canceled '
            body_html = 'Dear ' + self.create_uid.name + ',<br/>'
            if self._name == 'helpdesk.incident':
                subject = 'Your Incident Reported Is Canceled ' + self.number
                body_html += 'Incident Number ' + self.number + ' initiated by you is canceled.<br/><br/>Issue Title: ' \
                             + self.name + '.<br/>Description: ' + self.description + \
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'helpdesk.ftp':
                subject = 'Your FTP Request Is Canceled ' + self.number
                body_html += 'FTP request Number ' + self.number + ' initiated by you is canceled.<br/><br/>Destination: ' \
                             + self.destination.name + '.<br/>File/Folder: ' + self.name +\
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '

            elif self._name == 'helpdesk.cd':
                subject = 'Your CD/DVD request Is Canceled ' + self.number
                body_html += 'CD/DVD request Number ' + self.number + ' initiated by you is canceled.<br/><br/>Destination: ' \
                             + self.destination.name + '.<br/>Purpose: ' + self.purpose + \
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'site.package':
                target_site = ''
                application_type = ''
                if self.target_site_01:
                    target_site = self.target_site_01.name

                if self.application_type:
                    application_type = self.application_type.name
                subject = 'Your Site Package Request Is Canceled ' + self.number
                body_html += 'Site package request number ' + self.number + ' initiated by you is canceled.<br/><br/>3D Model Name: ' \
                             + self.name + '.<br/>Target Site: ' + target_site + \
                             '<br/>Application: '+application_type+'<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'asset.request':
                pc_type = ''
                application_type = ''
                if self.pc_type:
                    pc_type = self.pc_type.name

                if self.application_type:
                    application_type = self.application_type.name

                subject = 'Your PC request Is Canceled ' + self.number
                body_html += 'PC request ' + self.number + ' initiated by you is canceled.<br/><br/>' \
                             '<br/>Target Site: ' + pc_type + \
                             '<br/>Application: ' + application_type + \
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'asset.transfer':
                inventory_type = ''
                transfer_form = ''
                transfer_to = ''
                if self.inventory_type:
                    inventory_type = self.inventory_type.name

                if self.transfer_form:
                    transfer_form = self.transfer_form.name

                if self.transfer_to:
                    transfer_to = self.transfer_to.name

                subject = 'Your Asset Transfer Request Is Canceled ' + self.number
                body_html += 'Asset transfer request Number ' + self.number + ' initiated by you is canceled.<br/><br/>' \
                             'Inventory Type: ' + inventory_type + \
                             '<br/>Transfer From: ' + transfer_form + '<br/>Transfer To: '+transfer_to+'<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'asset.tracking':
                asset_id = ''
                if self.asset_id:
                    asset_id = self.asset_id.name

                subject = 'Your Common Asset Request Is Canceled ' + self.number
                body_html += 'Common Asset request number ' + self.number + ' initiated by you is canceled.<br/><br/>' \
                             'Request Subject: ' + self.name + \
                             '<br/>Asset: ' + asset_id + '<br/><br/>Start Date/Time: ' + self.request_start_date + \
                             '<br/>End Date/Time: '+self.request_end_date+\
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'stationary.request':
                subject = 'Your Stationary Request Is Canceled ' + self.number
                body_html += 'Stationary request number ' + self.number + ' initiated by you is canceled.<br/><br/>' \
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '
            elif self._name == 'library.tracking':
                subject = 'Your Book Request Is Canceled ' + self.number
                body_html += 'Book request number ' + self.number + ' initiated by you is canceled.<br/><br/>' \
                             '<div style="margin: 16px 0px 16px 0px;"><a href="' + self.website_url + \
                             '" style="background-color: #ffcb05; padding: 8px 16px 8px 16px; text-decoration: none; ' \
                             'color: #000000; border-radius: 5px; font-size:13px;"> View Request </a></div>This is ' \
                             'system-generated email. Please do not respond.<br/>Regards, '

            template_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': email_to,
                'email_cc': email_cc,
                'auto_delete': False,
            }
            mail_id = self.env["email.template"].sudo().create({'name': subject})
            template_id.write(template_values)
            template_id.send_mail(mail_id.id, force_send=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        result = super().fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)

        # Disabling the import button for users who are not in import group
        if view_type == 'tree':
            doc = etree.XML(result['arch'])
            if self.env.user.has_group('kts_workflow.group_defence_user'):
                # When the user is not part of the import group
                for node in doc.xpath("//tree"):
                    # Set the import to false
                    node.set('import', 'false')
            result['arch'] = etree.tostring(doc)

        return result


WorkflowValidation()
