# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
import random
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

class BaseModelExtend(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def search_records(self, args, offset=0, limit=80, order=None, count=False):
        res= self.search( args, offset, limit, order, count)
        request.simulab_rest_api = 1 #SUBODH:: This is temporarily added for local enviroment
        if request.simulab_rest_api:
            return {'return_data_as_record_set':True, 'records': res, 'model':self}
        return res

    @api.model
    def fields_get_queried_keys(self):
        return '{*}'

    def update_record(self, vals={}):
        super().write(vals)

class View(models.Model):
    _inherit = 'ir.ui.view'

    def _render_template(self, template, values=None, engine='ir.qweb'):
        if template in ['web.login', 'web.webclient_bootstrap']:
            if not values:
                values = {}
            values["title"] = self.env['ir.config_parameter'].sudo().get_param("app_system_name", "Simulab")
        return super(View, self)._render_template(template, values=values, engine=engine)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_system_name = fields.Char('System Name', default="Simulab")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()
        app_system_name = ir_config.get_param('app_system_name', default='Simulab')
        res.update(
            app_system_name=app_system_name
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_config = self.env['ir.config_parameter'].sudo()
        ir_config.set_param("app_system_name", self.app_system_name or "")

    def set_module_url(self):
        sql = "UPDATE ir_module_module SET website = '%s' WHERE license like '%s' and website <> ''" % \
              (self.app_enterprise_url, 'OEEL%')
        try:
            self._cr.execute(sql)
            self._cr.commit()
        except Exception as e:
            pass


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signup_token = fields.Char(copy=False, groups="base.group_erp_manager,simulab.group_simulab_administration,simulab.group_school_administration")
    signup_type = fields.Char(string='Signup Token Type', copy=False,  groups="base.group_erp_manager,simulab.group_simulab_administration,simulab.group_school_administration")
    signup_expiration = fields.Datetime(copy=False,  groups="base.group_erp_manager,simulab.group_simulab_administration,simulab.group_school_administration")


class SimulabPeriodicUpdate(models.Model):
    _name = 'simulab.periodic.update'

    def simulab_daily_update(self):
        self.env['simulab.course'].sudo().search([]).sudo().compute_simulab_course_stat()
        self.env['simulab.homepage'].sudo().update_school_dashboard()
