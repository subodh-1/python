# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
import razorpay
from odoo import tools
import time


class SimulabSubscription(models.Model):
    _name = 'simulab.subscription'
    _description = 'Course Purchase Subscriptions'
    _rec_name = 'payment_source'
    _order = 'id DESC'

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,transaction_id,purchased_count,untaxed_amount,discount_amount,gst_amount,total_amount,write_date,payment_status,' \
                 'payment_source,course_id{id,sku_id,purchased_price,special_price_desc,total_exp_count,count_exp_completed,' \
                 'count_exp_in_progress,count_exp_not_started,enrolled_experiments{id,simulation_progress, simulation_time, ' \
                 'simulation_days, simulation_quiz_score, simulation_milestone, enrolled_course_id{id,name,' \
                 'course_id{id,members_count,name,experiment_ids{id,sequence,name, simulation_name}}}},school_id{id,name},owner,' \
                 'student_id{id,name},is_purchased,course_id{id,name,grade_id{id,name},subject_id{id,name},learning_details,' \
                 'trial_package,price,discounted_price,subscription_period,price_valid_date,price_desc,sequence,description, ' \
                 'user_id{id,name}, nbr_quiz, total_experiments,total_time,marks_ids{id,name},members_count, image_url,' \
                 ' experiment_ids{id,sequence,name, simulation_name,image_url,subject_id{id,name}, marks_ids{id,name}, ' \
                 'completion_time, description}}},student_id{id,name},school_id{id,name}, payment_order_id}'
        return fields

    transaction_id = fields.Char('Transaction Id')
    payment_order_id = fields.Char('Order Id')
    server_pre_response = fields.Text('Payment Pre Payment Server Response')
    server_post_response = fields.Text('Payment Post Payment Server Response')

    untaxed_amount = fields.Monetary("Untaxed Amount", currency_field='company_currency')
    discount_amount = fields.Monetary("Discounted Amount", currency_field='company_currency')
    gst_amount = fields.Monetary("GST Amount", currency_field='company_currency')
    total_amount = fields.Monetary("Total Amount", currency_field='company_currency')

    write_date = fields.Datetime("Invoice Date")
    create_date = fields.Datetime(string="Order Date")

    payment_status = fields.Selection([
        ('inprocess', 'In Process'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ],
        'Payment Status', default="new")

    payment_source = fields.Selection([
        ('offline_payment', 'Offline Payment'),
        ('trial_package_auto_payment', 'Trial Package Auto Payment'),
        ('web_payment_gateway', 'Web Payment Gateway'),
        ('win_payment_gateway_razorpay', 'Windows App RazorPay'),
        ('android_admin_app_razorpay', 'Android Admin RazorPay'),
        ('google_in_app_payment', 'Google In App Payment'),
    ],
        'Payment Source', default="offline_payment")

    course_id = fields.Many2one('enrolled.course', string="Enrolled Course")
    course_simulab_id = fields.Char(string="Course Id", related='course_id.simulab_id')

    class_id = fields.Many2one('school.standard', related="course_id.class_id", store=True)
    company_currency = fields.Many2one("res.currency", string='Currency',
                                       related='company_id.currency_id', readonly=True, store=True)
    student_id = fields.Many2one('student.student', string="Student")
    mobile = fields.Char(related='student_id.mobile', store=True)

    school_id = fields.Many2one('simulab.school', string="School")
    company_id = fields.Many2one('res.company', "Company",
                                 related="school_id.company_id", store=True,
                                 help='''Select Company for this Student''')

    razorpay_status = fields.Char('RazorPay Status')
    razorpay_payment_id = fields.Char('RazorPay Payment Id')
    razorpay_order_id = fields.Char('RazorPay Order Id')
    razorpay_signature = fields.Char('RazorPay Signature')

    simulab_id = fields.Char('Simulab Id', readonly=1)
    purchased_count = fields.Integer("Purchased Count", default=1,
                                     help='Total students who has purchased in this transaction')


    @api.onchange('course_id')
    def _onchange_course_id(self):
        for rec in self:
            if rec.course_id:
                rec.untaxed_amount = rec.course_id.price
                rec.gst_amount = rec.course_id.price
                rec.discount_amount = rec.course_id.purchased_price if rec.course_id.purchased_price else rec.course_id.discounted_price
                rec.total_amount = rec.discount_amount

    @api.model
    def get_new_subscription(self, vals):
        res = self.create(vals)
        return {"id": res.id}

    @api.model
    def update_subscription(self, vals):
        id=vals.get("id",False)
        #id = int(vals.get("id", False)) # SUBODH:: Added for testing
        if not id:
            return {"id":0}
        del vals["id"]
        sub=self.browse(id)
        sub.write(vals)
        return {"id": id}

    @api.model
    def create(self, vals):
        vals['simulab_id'] = self.env['ir.sequence'].next_by_code(
            'enrolled.course.purchase.subscription')
        vals = self.prepare_subscription_data(vals)
        res = super().create(vals)
        if res.payment_status == 'success' and res.course_id.is_purchased == False:
            res.course_id.buy_now()
            self.create_order_purchase_success_notification(self.course_id, self.create_uid)
        return res

    def write(self, vals):
        res = super().write(vals)

        payment_status = vals.get('payment_status', False)

        if self.payment_status == 'success' and self.course_id.is_purchased == False:
            self.course_id.buy_now()

        if payment_status:
            if payment_status == 'success':
                self.create_order_purchase_success_notification(self.course_id, self.create_uid)

            elif payment_status == "failed":
                self.create_order_purchase_failed_notification(self.course_id, self.create_uid)
        return res

    def create_order_purchase_success_notification(self, course_id, user_id):
        if self.student_id:
            notification_obj = self.env['simulab.notification']
            if course_id.class_id:
                notification_obj.create_course_buy_student_success_notification(course_id, self.total_amount,
                                                                                True)
            else:
                notification_obj.create_course_buy_student_success_notification(course_id, self.total_amount,
                                                                                False)
        elif user_id:
            simulab_user = user_id.simulab_user

            if simulab_user:
                if simulab_user == 'school_admin':
                    teacher = self.env['school.teacher'].search([('user_id', '=', user_id.id)])
                    if teacher:
                        notification_obj = self.env['simulab.notification']
                        notification_obj.create_bulk_buy_success_notification_to_admin(teacher,
                                                                                       course_id,
                                                                                       self.total_amount,
                                                                                       self.purchased_count)
                elif simulab_user == 'teacher':
                    teacher = self.env['school.teacher'].search([('user_id', '=', user_id.id)])
                    if teacher:
                        notification_obj = self.env['simulab.notification']
                        notification_obj.create_bulk_buy_success_notification_to_admin(teacher,
                                                                                       course_id,
                                                                                       self.total_amount,
                                                                                       self.purchased_count)
                elif simulab_user == 'student':
                    student = self.env['student.student'].search([('user_id', '=', user_id.id)])
                    if student:
                        notification_obj = self.env['simulab.notification']
                        if course_id.class_id:
                            notification_obj.create_course_buy_student_success_notification(course_id,
                                                                                            self.total_amount,
                                                                                            True)
                        else:
                            notification_obj.create_course_buy_student_success_notification(course_id,
                                                                                            self.total_amount,
                                                                                            False)

    def create_order_purchase_failed_notification(self, course_id, user_id):
        if self.student_id:
            notification_obj = self.env['simulab.notification']
            notification_obj.create_course_buy_student_failed_notification(self.student_id, self.total_amount)

        elif user_id:
            simulab_user = user_id.simulab_user

            if simulab_user:
                if simulab_user == 'school_admin':
                    teacher = self.env['school.teacher'].search([('user_id', '=', user_id.id)])
                    if teacher:
                        notification_obj = self.env['simulab.notification']
                        notification_obj.create_bulk_buy_failed_notification_to_admin(teacher, self.total_amount)

                elif simulab_user == 'teacher':
                    teacher = self.env['school.teacher'].search([('user_id', '=', user_id.id)])
                    if teacher:
                        notification_obj = self.env['simulab.notification']
                        notification_obj.create_bulk_buy_failed_notification_to_admin(teacher, self.total_amount)

                elif simulab_user == 'student':
                    student = self.env['student.student'].search([('user_id', '=', user_id.id)])
                    if student:
                        notification_obj = self.env['simulab.notification']
                        notification_obj.create_course_buy_student_failed_notification(student,
                                                                                       self.total_amount)

    def generate_razorpay_order(self, vals):
        enrolled_course_id = vals.get('enrolled_course_id', False)
        payment_source = vals.get('payment_source', False)

        enrolled_course = self.env['enrolled.course'].browse(enrolled_course_id)
        if not enrolled_course:
            return {'http_status': 200, 'status': "Error", 'message': "Invalid enrolled course"}

        if enrolled_course.course_id.trial_package:
            return {'http_status': 200, 'status': "Error", 'message': "Trial Package, no need to purchase."}

        razorpay_dev_id = tools.config['razorpay_dev_id']
        razorpay_dev_secret = tools.config['razorpay_dev_secret']

        razorpay_prod_id = tools.config['razorpay_prod_id']
        razorpay_prod_secret = tools.config['razorpay_prod_secret']

        purchased_count = 0
        if len(enrolled_course.child_ids) > 0:
            for line in enrolled_course.child_ids:
                if not line.is_purchased:
                    purchased_count = purchased_count + 1
        elif not enrolled_course.is_purchased:
            purchased_count = 1

        if purchased_count == 0:
            return {'http_status': 200, 'status': "Error", 'message': "All are already purchased."}

        entity_id = enrolled_course.school_id.id if enrolled_course.school_id else False
        entity = "SCH-"
        if not entity_id:
            entity_id = enrolled_course.student_id.id if enrolled_course.student_id else False
            entity = "STU-" if enrolled_course.student_id else False

        if not entity_id:
            return {'http_status': 200, 'status': "Error", 'message': "invalid enrolled course"}

        receipt = entity + str(entity_id) + "-COURSE-" + str(
            enrolled_course.course_id.id) + '-' + str(round(time.time() * 1000))

        amount = enrolled_course.purchased_price if enrolled_course.purchased_price else enrolled_course.discounted_price
        amount = amount * purchased_count

        client_id = razorpay_prod_id if razorpay_prod_id else razorpay_dev_id
        client = razorpay.Client(
            auth=(client_id, razorpay_prod_secret if razorpay_prod_secret else razorpay_dev_secret))

        DATA = {
            "amount": amount * 100,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "enrolled_course_id": str(enrolled_course.id),
                "course_id": str(enrolled_course.course_id.id),
                "school": str(
                    enrolled_course.school_id.name if enrolled_course.school_id else enrolled_course.student_id.name if enrolled_course.student_id else ""),
            }
        }
        response = client.order.create(data=DATA)

        new_subscription = self.create({"transaction_id": receipt, "course_id": enrolled_course.id,
                                        "school_id": enrolled_course.school_id.id if enrolled_course.school_id else False,
                                        "student_id": enrolled_course.student_id.id if enrolled_course.student_id else False,
                                        "untaxed_amount": enrolled_course.price * purchased_count,
                                        "discount_amount": enrolled_course.discounted_price * purchased_count,
                                        "total_amount": amount, "payment_source": payment_source,
                                        "payment_status": "inprocess",
                                        "server_pre_response": response,
                                        'purchased_count': purchased_count,
                                        "payment_order_id": response["id"]})

        response['list_price'] = enrolled_course.price * purchased_count
        response['subscription_id'] = new_subscription.id
        response['purchased_count'] = purchased_count
        response['razorpay_key_id'] = client_id

        return response

    def create_subscription(self, enrolled_course, payment_source=False):
        ret = self.create({'course_id': enrolled_course, 'payment_source': payment_source})
        return ret

    def prepare_subscription_data(self, v={}, enrolled_course=False, payment_source=False):
        enrolled_course = v.get('course_id', enrolled_course)
        payment_source = v.get('payment_source', payment_source)
        
        if isinstance(enrolled_course, int):
            enrolled_course = self.env['enrolled.course'].browse(enrolled_course)

        purchased_count = 0
        if len(enrolled_course.child_ids) > 0:
            for line in enrolled_course.child_ids:
                if not line.is_purchased:
                    purchased_count = purchased_count + 1
        elif not enrolled_course.is_purchased:
            purchased_count = 1

        entity_id = enrolled_course.school_id.id if enrolled_course.school_id else False
        entity = "SCH-"
        if not entity_id:
            entity_id = enrolled_course.student_id.id if enrolled_course.student_id else False
            entity = "STU-" if enrolled_course.student_id else False

        if not entity_id:
            return {'http_status': 200, 'status': "Error", 'message': "invalid enrolled course"}

        amount = enrolled_course.purchased_price if enrolled_course.purchased_price else enrolled_course.discounted_price
        amount = amount * purchased_count

        if enrolled_course.course_id.trial_package:
            amount = 0.0
            payment_source = "trial_package_auto_payment"

        receipt = entity + str(entity_id) + "-COURSE-" + str(
            enrolled_course.course_id.id) + '-' + str(round(time.time() * 1000))

        vals = {"transaction_id": receipt, "course_id": enrolled_course.id,
                "school_id": enrolled_course.school_id.id if enrolled_course.school_id else False,
                "student_id": enrolled_course.student_id.id if enrolled_course.student_id else False,
                "untaxed_amount": enrolled_course.price,
                "discount_amount": enrolled_course.discounted_price,
                "total_amount": amount, 
                "payment_source": payment_source, 
                "payment_status": "success",
                "payment_order_id": "admin-"+receipt,
                "company_id": enrolled_course.company_id.id if enrolled_course.company_id else False,
                }
        vals.update(v)
        return vals
