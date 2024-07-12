

import logging
from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)

class NotificationTemplate(models.Model):
    _name = 'notification.template'
    _description = 'Notification Template'
    _order = 'write_date desc'

    event_name = fields.Char("Event Name", required=True)
    description = fields.Char("Template Description")
    version = fields.Char("Template Version", required=True)

    channel_id = fields.Selection([
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('notification', 'Notification'),
    ],
        'Notification Channel', default="email")

    message_title = fields.Char("Message Title")
    message_body = fields.Text("Message Body") # Make message_body dynamic and editable
    email_template_id = fields.Many2one('mail.template', "Email Template")
    active = fields.Boolean(default=True,
                            help='Activate/Deactivate template record')

    write_date = fields.Datetime("Edit Date")
    create_date = fields.Datetime(string="Create Date")

    @api.depends('event_name')
    def _compute_message_body(self):
        for record in self:
            record.message_body = f'''Your school admin has added you as a teacher. Click on forgot password option to login to SimuLab Master App bit.ly/3HcBuqf using username: {record.event_name}.'''

    @api.model
    def fields_get_queried_keys(self):
        fields = '{event_name, description, version, message_title, message_body, email_template_id, channel_id, write_date, version}'
        return fields

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

    def write(self, vals):
        res = super().write(vals)
        return res
