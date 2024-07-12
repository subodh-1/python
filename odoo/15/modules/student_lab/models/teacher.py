# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.http import request


class SchoolTeacher(models.Model):
    '''Defining a Teacher information.'''

    _name = 'school.teacher'
    _description = 'Teacher Information'

    _inherit = [
        'simulab.email',
        'mail.thread',
        'mail.activity.mixin',
        'image.mixin',
    ]

    name = fields.Char("Name", help='Teacher Name')

    standard_ids = fields.Many2many('school.standard', 'school_class_rel',
                                    'teacher_id', 'class_id',
                                    'Assigned Classes',
                                    help='Standard for which the teacher\
                                  responsible for')

    school_id = fields.Many2one('simulab.school', "School",
                                help='Select school')

    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this teacher''')

    department_id = fields.Many2one('school.department', 'Department',
                                    help='Select department')

    phone = fields.Char("Phone Number", help='Teacher Phone')
    mobile = fields.Char("Mobile Number", help='Teacher Mobile')
    email = fields.Char("Email", help='Teacher Email id')
    email_verified = fields.Boolean('Email Verified')

    is_school_admin = fields.Boolean('School Admin',
                                     help='Select this if this is School Admin')

    active = fields.Boolean('Active', default=True,
                            help='Select this if active')
    user_id = fields.Many2one('res.users', 'Related User',
                              help='Related User')
    login = fields.Char("Login Id", related='user_id.login', store=True)

    notes = fields.Text("Notes")

    class_id = fields.Many2one('school.standard', 'Class',
                               help='Select teacher standard')
    image_url = fields.Char('Image Url', compute='_compute_image_url', compute_sudo=False, readonly=1, store=True)

    simulab_id = fields.Char('Simulab Id', readonly=1)

    @api.depends('image_1920')
    def _compute_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=school.teacher&id=' + str(
                    record.id) + '&field=image_1024'

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        for rec in self:
            if rec.standard_id:
                rec.school_id = rec.standard_id.school_id.id

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        return res

    @api.model
    def create(self, vals):
        """Inherited create method to assign value to users for delegation"""

        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.school.teacher')
        teacher_id = super().create(vals)
        user_id = vals.get('user_id', False)
        if not user_id:
            user_rec = self.create_teacher_login(teacher_id)
            user_id = user_rec.id
        teacher_id.write({'user_id': user_id})

        if teacher_id.standard_ids:
            teacher_id.standard_ids.compute_teachers()

        notification_obj = self.env['simulab.notification']
        notification_obj.create_teacher_added_notification(teacher_id)
        #self.env['simulab.homepage'].refresh_school_dashboard(teacher_id.school_id)
        return teacher_id

    def create_teacher_login(self, teacher_id, user_vals={}):
        user_obj = self.env['res.users']
        if not user_vals:
            user_vals = {'name': teacher_id.name,
                         'login': teacher_id.mobile or teacher_id.email,
                         'email': teacher_id.email,
                         }

        if teacher_id:
            company_id = teacher_id.school_id.company_id.id
            is_school_admin = teacher_id.is_school_admin
        else:
            company_id = user_vals.get('company_id')
            is_school_admin = user_vals.get('is_school_admin')

        user_vals['company_id'] = company_id
        user_vals['simulab_user'] = 'school_admin' if is_school_admin else 'teacher'

        company_vals = {'company_ids': [(4, int(company_id))]}
        user_vals.update(company_vals)
        ctx_vals = {'teacher_create': True,
                    'company_id': company_id,
                    'is_school_admin': is_school_admin
                    }

        user_rec = user_obj.with_context(ctx_vals).create(user_vals)
        return user_rec

    def write(self, vals):
        if 'mobile' in vals and vals['mobile']:
            user_id = self.env['res.users'].search([('login', '=', vals['mobile'])])
            if user_id:
                raise UserError(_("Mobile no %s already added as login for another user.") % vals['mobile'])

        ret = super().write(vals)
        self.clear_caches()
        if 'mobile' in vals and vals['mobile']:
            self.user_id.write({'login': vals['mobile']})

        if 'email' in vals:
            notification_obj = self.env['simulab.notification']
            notification_obj.email_add_notification(self.id, self.user_id, self.email, self.name)

        if 'standard_ids' in vals:
            self.standard_ids.compute_teachers()
        return ret

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name, image_url, standard_ids{id,name,standard_id{id,name},division_id{id,name},total_students,school_id{id,name}}, school_id{id,name,country_id{id,name,code,phone_code}}, company_id{id,name}, department_id{id,name}, phone, mobile, email, email_verified, is_school_admin,active, user_id{id,name}, notes}'
        return fields

    @api.model
    def get_teachers_list(self):
        return []
