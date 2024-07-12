# -*- coding: utf-8 -*-

from odoo import models, fields, api


# class immersive_trial_balance_report(models.Model):
#     _name = 'immersive_trial_balance_report.immersive_trial_balance_report'
#     _description = 'immersive_trial_balance_report.immersive_trial_balance_report'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()

#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class ImmersiveTrialBalanceReport(models.TransientModel):
    _name = 'immersive_trial_balance_report.immersive_trial_balance_report'
    _description = 'Immersive Trial Balance Report'

    account_id = fields.Many2one('account.account', string='Account')
    name = fields.Char(string='Account Name')
    internal_group = fields.Char(string='Internal Group')
    internal_type = fields.Char(string='Internal Type')
    opening_balance = fields.Float(string='Opening Balance')
    credit = fields.Float(string='Credit')
    debit = fields.Float(string='Debit')
    closing_balance = fields.Float(string='Closing Balance')

    @api.model
    def fetch_trial_balance_data(self):
        query = """
            SELECT 
                aa.id as account_id, aa.name, aa.internal_group, aa.internal_type,
                COALESCE(bb.debit - bb.credit, 0) as opening_balance,
                COALESCE(cc.credit, 0) as credit,
                COALESCE(cc.debit, 0) as debit,
                COALESCE(bb.debit - bb.credit, 0) + COALESCE(cc.debit, 0) - COALESCE(cc.credit, 0) as closing_balance
            FROM 
                account_account aa
            LEFT JOIN 
                (
                    SELECT account_id, SUM(debit) as debit, SUM(credit) as credit
                    FROM account_move_line
                    WHERE parent_state='posted' AND date < '2023-04-01'
                    GROUP BY account_id
                ) bb ON aa.id = bb.account_id
            LEFT JOIN 
                (
                    SELECT account_id, SUM(debit) as debit, SUM(credit) as credit
                    FROM account_move_line
                    WHERE parent_state='posted' AND date > '2023-04-01' AND date <= '2024-03-31'
                    GROUP BY account_id
                ) cc ON aa.id = cc.account_id
            ORDER BY aa.internal_group, aa.internal_type
        """
        self.env.cr.execute(query)
        trial_balance_data = self.env.cr.dictfetchall()
        
        # Clear any existing data
        self.search([]).unlink()
        
        # Create records in the transient model
        for data in trial_balance_data:
            self.create(data)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Trial Balance',
            'res_model': 'immersive_trial_balance_report.immersive_trial_balance_report',
            'view_mode': 'tree',
            'target': 'new',
        }

