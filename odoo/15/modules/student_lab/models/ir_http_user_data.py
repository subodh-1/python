# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """ Add information about iap enrich to perform """
        session_info = super(Http, self).session_info()
        if request.httprequest.user_agent and request.httprequest.user_agent.browser:
            return session_info

        teacher_id = request.env['school.teacher'].sudo().search([('user_id','=',session_info["uid"])])
        teacher_id = teacher_id.id if teacher_id else False
        if teacher_id:
            session_info['teacher_id']=teacher_id

        student_ids = request.env['student.student'].sudo().search([('user_id','=',session_info["uid"])])
        if student_ids:
            session_info['student_ids']=[id.id for id in student_ids]

        user = request.env['res.users'].sudo().browse(session_info["uid"])
        if user:
            session_info['simulab_user']=user.simulab_user

        return session_info