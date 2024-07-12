# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.http import request


class SimulabFAQCategory(models.Model):
    _name = 'simulab.faq.category'
    _description = 'FAQ Categories'
    _rec_name = 'name'

    name = fields.Char('Name', required=True, translate=True)
    desc = fields.Html('Description')
    category_type = fields.Selection([
        ('student', 'Student'),
        ('admin', 'Admin'),
        ],
        'Category Type', default="student")

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,desc,category_type}'
        return fields

class SimulabFAQ(models.Model):

    _name = 'simulab.faq'
    _description = 'Simulab FAQs'
    _rec_name = 'faq_category_id'


    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,question,answer,faq_category_id{id,name,desc,category_type}}'
        return fields

    question = fields.Html('Question', required=True)
    answer = fields.Html('Answer', required=True)
    faq_category_id = fields.Many2one('simulab.faq.category', string="Category")
    category_type = fields.Selection(related="faq_category_id.category_type")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

    def write(self, vals):
        res= super().write(vals)
        return res
