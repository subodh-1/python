# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models


class SimulabCourseTagGroup(models.Model):
    _name = 'simulab.course.tag.group'
    _description = 'Simulab Course Groups'
    _order = 'sequence asc'

    name = fields.Char('Group Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10, index=True, required=True)
    tag_ids = fields.One2many('simulab.course.tag', 'group_id', string='Tags')

    def _default_is_published(self):
        return True


class SimulabCourseTag(models.Model):
    _name = 'simulab.course.tag'
    _description = 'Simulab Course Tag'
    _order = 'group_sequence asc, sequence asc'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10, index=True, required=True)
    group_id = fields.Many2one('simulab.course.tag.group', string='Group', index=True, required=True)
    group_sequence = fields.Integer(
        'Group sequence', related='group_id.sequence',
        index=True, readonly=True, store=True)
    course_ids = fields.Many2many('simulab.course', 'simulab_sourse_tag_rel', 'tag_id', 'course_id', string='Courses')
    color = fields.Integer(
        string='Color Index', default=lambda self: randint(1, 11),
        help="Tag color used in both backend and website. No color means no display in kanban or front-end, to distinguish internal tags from public categorization tags")
