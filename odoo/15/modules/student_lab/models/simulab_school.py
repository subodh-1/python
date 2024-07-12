# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import os
import re

from odoo import api, fields, models, tools, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.modules.module import get_resource_path
from random import randrange
from PIL import Image
from odoo import SUPERUSER_ID
import copy

_logger = logging.getLogger(__name__)


class SimulabSchool(models.Model):
    _name = "simulab.school"
    _description = 'Schools/Institutes'
    _order = 'sequence, name'

    def copy(self, default=None):
        raise UserError(
            _('Duplicating a school is not allowed. Please create a new school instead.'))

    def _get_logo(self):
        return base64.b64encode(open(
            os.path.join(tools.config['root_path'], 'addons', 'base', 'static', 'img',
                         'res_company_logo.png'), 'rb').read())

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    def _get_default_favicon(self, original=False):
        img_path = get_resource_path('web', 'static/img/favicon.ico')
        with tools.file_open(img_path, 'rb') as f:
            if original:
                return base64.b64encode(f.read())
            # Modify the source image to add a colored bar on the bottom
            # This could seem overkill to modify the pixels 1 by 1, but
            # Pillow doesn't provide an easy way to do it, and this 
            # is acceptable for a 16x16 image.
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            original = Image.open(f)
            new_image = Image.new('RGBA', original.size)
            height = original.size[1]
            width = original.size[0]
            bar_size = 1
            for y in range(height):
                for x in range(width):
                    pixel = original.getpixel((x, y))
                    if height - bar_size <= y + 1 <= height:
                        new_image.putpixel((x, y), (color[0], color[1], color[2], 255))
                    else:
                        new_image.putpixel((x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
            stream = io.BytesIO()
            new_image.save(stream, format="ICO")
            return base64.b64encode(stream.getvalue())

    name = fields.Char(string='School Name', required=True)
    logo = fields.Binary(default=_get_logo, string="School Logo", store=True)
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    zip = fields.Char(string="Pin Code")

    state_id = fields.Many2one(
        'res.country.state', string="State", domain="[('country_id', '=?', country_id)]"
    )
    res_city = fields.Many2one("res.city", string="City",
                               domain="[('state_id', '=', state_id)]")
    city = fields.Char(string="City", related="res_city.name", store=True)

    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    website = fields.Char(string="Website")
    punch_line = fields.Char(string="Punch-Line")
    favicon = fields.Binary(string="School Favicon",
                            help="This field holds the image used to display a favicon for a given school.",
                            default=_get_default_favicon)
    student_id = fields.Many2one('student.student')
    simulab_id = fields.Char('Simulab Id', readonly=1)
    company_id = fields.Many2one('res.company', 'Company', ondelete="cascade",
                                 required=False, delegate=True,
                                 help='Company_id of the school')
    standards = fields.One2many('school.standard', 'school_id',
                                'Standards', help='School standard')
    country_id = fields.Many2one('res.country', string="Country", default=104)

    exp_completed = fields.Integer("Experiment Completed", compute="compute_exp_stats", store=True)
    exp_completed_ontime = fields.Integer("Experiment Completed On Time",
                                          compute="compute_exp_stats", store=True)
    exp_overdue = fields.Integer("Experiment Overdue", compute="compute_exp_stats", store=True)
    quiz_completed = fields.Integer("Quiz Completed", compute="compute_quiz_status", store=True)
    quiz_completed_ontime = fields.Integer("Quiz Completed Ontime", compute="compute_quiz_status",
                                           store=True)
    quiz_passed = fields.Integer("Quiz Completed", compute="compute_quiz_status", store=True)
    quiz_failed = fields.Integer("Quiz Failed", compute="compute_quiz_status", store=True)
    quiz_overdue = fields.Integer("Quiz Overdue", compute="compute_quiz_status", store=True)

    def compute_exp_stats(self):
        for record in self:
            record.exp_completed = 0
            record.exp_completed_ontime = 0
            record.exp_overdue = 0

    def compute_quiz_status(self):
        for record in self:
            record.quiz_completed = 0
            record.quiz_completed_ontime = 0
            record.quiz_passed = 0
            record.quiz_failed = 0
            record.quiz_overdue = 0

    @api.model
    def fields_get_queried_keys(self):
        fields = "{exp_completed, exp_completed_ontime, exp_overdue, quiz_completed, quiz_completed_ontime, quiz_passed, quiz_failed, quiz_overdue, name,logo,punch_line,street,street2,zip,city,state_id{id,name},email,phone,mobile,website,vat,favicon,simulab_id,country_id{id,name}}"
        return fields

    @api.model
    def create(self, vals):
        if not vals.get('favicon'):
            vals['favicon'] = self._get_default_favicon()
        if not vals.get('name') or vals.get('partner_id'):
            self.clear_caches()
            return super().create(vals)
        partner = self.env['res.partner'].create({
            'name': vals['name'],
            'is_company': True,
            'image_1920': vals.get('logo'),
            'email': vals.get('email'),
            'phone': vals.get('phone'),
            'website': vals.get('website'),
            'vat': vals.get('vat'),
            'country_id': vals.get('country_id'),
        })
        # compute stored fields, for example address dependent fields
        partner.flush()
        vals['partner_id'] = partner.id
        self.clear_caches()

        company_vals = copy.deepcopy(vals)
        if 'res_city' in company_vals:
            del company_vals['res_city']
        if 'punch_line' in company_vals:
            del company_vals['punch_line']
        company = self.env['res.company'].sudo().create(company_vals)
        self.add_company(company.id)
        # The write is made on the user to set it automatically in the multi company group.
        self.env.user.write({'company_ids': [Command.link(company.id)]})

        # Make sure that the selected currency is enabled
        if vals.get('currency_id'):
            currency = self.env['res.currency'].browse(vals['currency_id'])
            if not currency.active:
                currency.write({'active': True})

        vals['company_id'] = company.id

        vals['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.school')
        school = super().sudo().create(vals)
        return school

    def write(self, values):
        res = super().write(values)
        company_fields = ['name', 'logo', 'street', 'street2', 'zip', 'city', 'state_id', 'email',
                          'phone', 'mobile', 'website', 'vat', 'favicon', 'company_id']
        v = {}
        for key in values.keys():
            if key in company_fields:
                v[key] = values[key]
        if v:
            self.company_id.write(values)
        return res

    def add_company(self, company_id):
        simulab_users = self.env['res.users'].search([('simulab_user', '=', 'simulab_admin')])
        for user in simulab_users:
            company_ids = [comp.id for comp in user.company_ids]
            if company_id not in company_ids:
                company_ids = company_ids + [company_id]
                company_id = self.env['ir.config_parameter'].sudo().get_param(
                    'default.student.company')
                if company_id not in company_ids:
                    company_ids = company_ids + [int(company_id)]
                company_ids = [(6, 0, company_ids)]
                user.write({'company_ids': company_ids})
