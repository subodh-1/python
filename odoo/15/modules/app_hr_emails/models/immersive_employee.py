# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
  
    
class ImmersiveHrEmails(models.Model):    
        
    _inherit = "hr.employee"
    
    # _name = 'immersive.hr.emails'
    # _description = 'Immersive HR Emails'  
    
    
    @api.model
    def send_birthday_emails(self):
        month = date.today().month
        day = date.today().day
        
        for employee in self.search([('active', '=', True), ('birthday', '!=', False)]):
            if employee.birthday.day == day and employee.birthday.month == month:
                #if employee.id == 88: #SUBODH :: For testing
                self.env.ref('immersive_hr_emails.mail_template_birthday_wish').send_mail(employee.id, force_send=True)
                all_email = self.search([('id', '!=', employee.id), ('active', '=', True)]).mapped('work_email')
                #all_email = [('subodh.choure@immersivelabz.com')] #SUBODH :: For testing
                email_values = {'email_to': ','.join(all_email)}
                self.env.ref('immersive_hr_emails.mail_template_birthday_reminder').send_mail(employee.id, email_values=email_values, force_send=True)

    @api.model
    def send_anniversary_emails(self):
        month = date.today().month
        day = date.today().day
        year = date.today().year
        for employee in self.search([('active', '=', True), ('doj', '!=', False)]):           
            if employee.doj.day == day and employee.doj.month == month and employee.doj.year !=year:
                #if employee.id == 88:
                self.env.ref('immersive_hr_emails.mail_template_anniversary_wish').send_mail(employee.id, force_send=True)
                all_email = self.search([('id', '!=', employee.id), ('active', '=', True)]).mapped('work_email')
                #all_email = [('subodh.choure@immersivelabz.com')]
                email_values = {'email_to': ','.join(all_email)}
                self.env.ref('immersive_hr_emails.mail_template_anniversary_reminder').send_mail(employee.id, email_values=email_values, force_send=True)
