from odoo import http
from odoo.http import request


class ImmersiveTrialBalanceReport(http.Controller):
    @http.route('/immersive_trial_balance_report/immersive_trial_balance_report', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/immersive_trial_balance_report/immersive_trial_balance_report/objects', auth='public')
    def list(self, **kw):
        # Call the fetch_trial_balance_data method to fetch trial balance data
        trial_balance_data = request.env['immersive_trial_balance_report.immersive_trial_balance_report'].fetch_trial_balance_data()
        
        # Return the trial balance data to the template
        return http.request.render('immersive_trial_balance_report.listing', {
            'trial_balance_data': trial_balance_data,
        })

    @http.route('/immersive_trial_balance_report/immersive_trial_balance_report/objects/<model("immersive_trial_balance_report.immersive_trial_balance_report"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('immersive_trial_balance_report.object', {
            'object': obj
        })
