# -*- coding: utf-8 -*-
from odoo import http


class ImmersiveTrialBalanceReport(http.Controller):
    @http.route('/immersive_trial_balance_report/immersive_trial_balance_report', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/immersive_trial_balance_report/immersive_trial_balance_report/objects', auth='public')
    def list(self, **kw):
        return http.request.render('immersive_trial_balance_report.listing', {
            'root': '/immersive_trial_balance_report/immersive_trial_balance_report',
            'objects': http.request.env['immersive_trial_balance_report.immersive_trial_balance_report'].search([]),
        })

    @http.route('/immersive_trial_balance_report/immersive_trial_balance_report/objects/<model("immersive_trial_balance_report.immersive_trial_balance_report"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('immersive_trial_balance_report.object', {
            'object': obj
        })
