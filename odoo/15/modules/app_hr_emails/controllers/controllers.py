# -*- coding: utf-8 -*-
# from odoo import http


# class ImmersiveEmployee(http.Controller):
#     @http.route('/immersive_employee/immersive_employee', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/immersive_employee/immersive_employee/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('immersive_employee.listing', {
#             'root': '/immersive_employee/immersive_employee',
#             'objects': http.request.env['immersive_employee.immersive_employee'].search([]),
#         })

#     @http.route('/immersive_employee/immersive_employee/objects/<model("immersive_employee.immersive_employee"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('immersive_employee.object', {
#             'object': obj
#         })
