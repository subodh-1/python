# See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ResUsers(models.Model):

    _inherit = "res.users"
    _order = 'create_date desc'

    simulab_user = fields.Selection([
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school_admin', 'School Admin'),
        ('simulab_admin', 'Simulab Admin')])
    login_date = fields.Datetime(related='log_ids.create_date', string='Latest authentication', readonly=False, store=True)
    managed_user = fields.Boolean(string='Managed User', default=False)

    @api.model
    def create(self, vals):
        if not vals.get('company_id', False):
            vals.update({'company_id':self._context.get('company_id')})
            vals.update({'company_ids':[(4, self._context.get('company_id'))]})
        user_rec = super(ResUsers, self).create(vals)
        user_rec.update_user_create_groups(vals)
        return user_rec

    def write(self, vals):
        user_rec = super().write(vals)
        self.update_user_create_groups(vals)
        return user_rec

    def update_user_create_groups(self, vals):
        if not vals.get('simulab_user', False):
            return

        if self.simulab_user=='simulab_admin':
            teacher_grp_id = self.env.ref('simulab.group_simulab_administration')
        elif self.simulab_user=='school_admin':
            teacher_grp_id = self.env.ref('simulab.group_school_administration')
        elif self.simulab_user=='teacher':
            teacher_grp_id = self.env.ref('simulab.group_school_teacher')
        elif self.simulab_user=='student':
            student_grp_id = self.env.ref('simulab.group_school_student')
            user_base_grp = self.env.ref('base.group_user')
            student_group_ids = [user_base_grp.id, student_grp_id.id]
            super().write({'groups_id': [(6, 0, student_group_ids)]})
            return
        else:
            return

        user_base_grp = self.env.ref('base.group_user')
        contact_create = self.env.ref('base.group_partner_manager')
        teacher_group_ids = [user_base_grp.id, teacher_grp_id.id,
                             contact_create.id]
        super().write({'groups_id': [(6, 0, teacher_group_ids)]})

    @api.model
    def fields_get_queried_keys(self):
        fields ='{id,name, login, company_id{id,name},user_companies{id,name},active}'
        return fields

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        res= super().search_read(domain, fields, offset, limit, order)
        return res

    def search(self, args, offset=0, limit=None, order=None, count=False):
        res= super().search(args, offset, limit, order, count)
        return res