# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
import requests
import PyPDF2

from dateutil.relativedelta import relativedelta
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import sql
from odoo.tools import is_html_empty
from random import randint
from odoo.http import request


class SimulabExperimentLink(models.Model):
    _name = 'simulab.experiment.link'
    _description = "External URL for a particular experiment"

    experiment_id = fields.Many2one('simulab.experiment', required=True, ondelete='cascade')
    name = fields.Html('Title', required=True)
    link = fields.Html('Link', required=True)


class SimulabExperimentObject(models.Model):
    _name = 'simulab.experiment.object'
    _description = "Experiment Object Having Single Image and One Description"
    _inherit = [
        'image.mixin',
    ]
    experiment_simulation_id = fields.Many2one('simulab.experiment', ondelete='cascade')
    experiment_funfact_id = fields.Many2one('simulab.experiment', ondelete='cascade')
    experiment_theory_id = fields.Many2one('simulab.experiment', ondelete='cascade')
    experiment_theory_technique_id = fields.Many2one('simulab.experiment', ondelete='cascade')
    exp_qna_id = fields.Many2one('simulab.experiment', ondelete='cascade')

    name = fields.Html('Title')
    experiment_info = fields.Text(string='Experiment Info')
    description_html = fields.Html('Fun Fact', translate=True)
    description = fields.Text('Description', compute='_compute_text_details', store=True)
    image_url = fields.Char('Image Url', compute='_compute_exp_image_url', compute_sudo=False,
                            readonly=1, store=True)

    @api.depends('image_1920')
    def _compute_exp_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=simulab.experiment.object&id=' + str(
                    record.id) + '&field=image_1024'

    @api.depends('description_html')
    def _compute_text_details(self):
        for record in self:
            record.description = ''
            if not is_html_empty(record.description_html):
                description = self.env['ir.fields.converter'].text_from_html(
                    record.description_html, 20)
                record.description = description


class SimulabExperimentTag(models.Model):
    """ Tag to search experiments across channels. """
    _name = 'simulab.experiment.tag'
    _description = 'Simulab Experiment Tag'

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer(
        string='Color Index', default=lambda self: randint(1, 11),
        help="Tag color used in both backend and website. No color means no display in kanban or front-end, to distinguish internal tags from public categorization tags")

    _sql_constraints = [
        ('experiment_tag_unique', 'UNIQUE(name)', 'A tag must be unique!'),
    ]


class SimulabExperiment(models.Model):
    _name = 'simulab.experiment'
    _inherit = [
        'mail.thread',
        'image.mixin',
    ]
    _description = 'Simulab Experiments'
    _order_by_strategy = {
        'sequence': 'sequence asc, id asc',
        'most_viewed': 'total_views desc',
        'latest': 'date_published desc',
    }
    _order = 'sequence asc, id asc'

    # description
    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean(default=True, tracking=100)
    sequence = fields.Integer('Sequence', default=0)
    user_id = fields.Many2one('res.users', string='Uploaded by', default=lambda self: self.env.uid)
    grade_id = fields.Many2one('standard.standard', string='Grade')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    exp_header = fields.Html('Header', translate=True)
    exp_qna = fields.One2many('simulab.experiment.object', 'exp_qna_id', string="Q&A")

    preview = fields.Html('Preview', translate=True)
    summary = fields.Html('Summary', translate=True)
    objective = fields.Html('Objective', translate=True)
    description = fields.Html('Description', translate=True)
    theory_links = fields.One2many('simulab.experiment.link', 'experiment_id',
                                   string="Theory Links")

    experiment_details = fields.Html('Description', compute='_compute_experiment_details',
                                     translate=True, store=True)

    tag_ids = fields.Many2many('simulab.experiment.tag', 'rel_experiment_tag', 'experiment_id',
                               'tag_id', string='Tags')
    is_new_experiment = fields.Boolean('Is New Slide', compute='_compute_is_new_experiment')
    completion_time = fields.Float('Duration', digits=(10, 4),
                                   help="The estimated completion time for this experiment")
    is_published = fields.Boolean(string="Publish", default=False)

    quiz_ids = fields.One2many("experiment.quiz", "experiment_id", string="Quizes")
    questions_count = fields.Integer(string="Numbers of Questions",
                                     compute='_compute_questions_count')

    date_published = fields.Datetime('Publish Date', readonly=True, tracking=1)
    likes = fields.Integer('Likes', compute='_compute_like_info', store=True, compute_sudo=False)
    dislikes = fields.Integer('Dislikes', compute='_compute_like_info', store=True,
                              compute_sudo=False)
    user_vote = fields.Integer('User vote', compute='_compute_user_membership_id',
                               compute_sudo=False)
    total_views = fields.Integer("Views", default="0", compute='_compute_total', store=True)
    comments_count = fields.Integer('Number of comments', compute="_compute_comments_count")
    nbr_quiz = fields.Integer("Number of Quizs", compute="_compute_experiments_statistics",
                              store=True)
    total_experiments = fields.Integer(compute='_compute_experiments_statistics', store=True)
    members_count = fields.Integer('Enrolled Student', compute='_compute_members_count',
                                   compute_sudo=True, store=True)

    marks_ids = fields.Many2many(
        'student.exams.marks', 'exam_marks_simulab_experiment_rel', 'exam_id', 'experiment_id',
        string='Marks')

    fun_fcts = fields.One2many('simulab.experiment.object', 'experiment_funfact_id',
                               string="Fun Facts")
    simulation_stories = fields.One2many('simulab.experiment.object', 'experiment_simulation_id',
                                         string="Simulation Story")
    theory_details = fields.One2many('simulab.experiment.object', 'experiment_theory_id',
                                     string="Theory Details")
    theory_techniques = fields.One2many('simulab.experiment.object',
                                        'experiment_theory_technique_id', string="Theory Technique")

    simulab_id = fields.Char('Simulab Id', readonly=1)

    image_url = fields.Char('Experiment Image Url', compute='_compute_exp_image_url',
                            compute_sudo=False, readonly=1, store=True)
    completion_days = fields.Integer('Experiment Completion in Days',
                                     help='No of days by when experiment should be completed from scheduled date.')
    simulation_name = fields.Char('Simulation Name')

    theory_text = fields.Char(compute='_theory_details_display')
    theory_image = fields.Html(compute='_theory_details_display', store=False)

    fun_fcts_text = fields.Char(compute='_details_fun_fcts')
    fun_image = fields.Html(compute='_details_fun_fcts', store=False)

    simulation_stories_text = fields.Char(compute='_simulation_stories_display')
    simulation_stories_image = fields.Html(compute='_simulation_stories_display', store=False)

    theory_techniques_text = fields.Char(compute='_theory_techniques_display')
    theory_techniques_image = fields.Html(compute='_theory_techniques_display', store=False)

    student_experiment_id = fields.Integer('Student Experiment Id', compute='_compute_student_experiment',
                                   compute_sudo=True)
    
    #SUBODH:: New field for medium for Odhisha board changes
    medium_id = fields.Many2one('edu.medium', string="Education Medium", required=True)    
    #parent_id = fields.Integer('Parent Experiment', optional=True)
    parent_id = fields.Many2one('simulab.experiment', string='Parent Experiment', optional=True)
 
   
    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        values = {}
        
        if self.parent_id:
            pass
            #raise UserError(f"You cannot change the medium for a child experiment.{self.parent_id}")
        
        read_only_fields = ['active','medium_id','parent_id','simulation_name','grade_id','subject_id','user_id','completion_days','tag_ids']
            
        # existing_experiment = self.env['simulab.experiment'].search(
        #         [('id', '=', self.parent_id), ('medium_id', '=', self.medium_id.id)])
        if not self.parent_id.exists():
            return
        existing_experiment = self.env['simulab.experiment'].search(
                [('id', '=', self.parent_id.id)])   
            
        if existing_experiment: 
            experiment = existing_experiment[0] 
           
            try:
                
                for field_name, field in experiment.fields_get().items():
                    if field_name in experiment:           
                        if field_name in read_only_fields:               
                            if field.get('type') == 'many2one':
                                related_record = getattr(experiment, field_name)
                                values[field_name] = related_record.id if related_record else False
                            else:
                                values[field_name] = getattr(experiment, field_name) 
                            if field_name == 'parent_id':
                                values[field_name] = self.parent_id.id                                
                                           
            except Exception as e:
                pass    
            return {'value': values}    

    def _compute_student_experiment(self):
        for record in self:
            record.student_experiment_id=0
            logged_user = self.env.user.id
            student_ids = self.env['student.student'].search([('user_id', '=', logged_user)])
            if student_ids:
                res = self.env['student.experiment'].search([('experiment_id', '=', record.id), ('student_id', '=', student_ids[0].id)])
                if res:
                    record.student_experiment_id=res[0].id

    def _simulation_stories_display(self):
        for record in self:
            record.simulation_stories_image = None
            record.simulation_stories_text = ""
            for simulation_storie in record.simulation_stories:
                record.simulation_stories_text = simulation_storie.description
                record.simulation_stories_image = "<img src='" + simulation_storie.image_url + "' style='width: 150px;height: 150px;'/>"
                break

    def _theory_techniques_display(self):
        for record in self:
            record.theory_techniques_image = None
            record.theory_techniques_text = ""
            for theory_technique in record.theory_techniques:
                record.theory_techniques_text = theory_technique.description
                record.theory_techniques_image = "<img src='" + theory_technique.image_url + "' style='width: 150px;height: 150px;'/>"
                break

    def _details_fun_fcts(self):
        for record in self:
            record.fun_image = None
            record.fun_fcts_text = ""
            for fun_fct in record.fun_fcts:
                record.fun_fcts_text = fun_fct.description
                record.fun_image = "<img src='" + fun_fct.image_url + "' style='width: 150px;height: 150px;'/>"
                break

    def _theory_details_display(self):
        for record in self:
            record.theory_text = ""
            for theory in record.theory_details:
                record.theory_text = theory.description
                record.theory_image = "<img src='" + theory.image_url + "' style='width: 150px;height: 150px;'/>"
                break

    def action_experiment_click(self):
        result = self.env['ir.actions.act_window']._for_xml_id('simulab.simulab_experiment_action1')
        result.update({
            'res_id': self.id,
            'domain': [('id', '=', self.id)],
            'context': dict(
                self.env.context,
                experiment_id=self.id,
                create=False,
                edit=False,
                no_breadcrumbs=True,
            ),
        })
        return result

    def simulab_experiments(self, params={'subject_id': 'phy'}):
        search_term = []
        for p in params.keys():
            search_term = search_term + [(p, 'ilike', params[p])]

        exp = self.env['simulab.experiment'].search(search_term)
        return {'return_data_as_record_set': True, 'records': exp,
                'model': self.env['simulab.experiment']}

    @api.depends('image_1920')
    def _compute_exp_image_url(self):
        for record in self:
            record.image_url = False
            if record.image_1920:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.image_url = base_url + '/web/image?' + 'model=simulab.experiment&id=' + str(
                    record.id) + '&field=image_1024'

    def _compute_members_count(self):
        for record in self:
            record.members_count = self.env['student.experiment'].search_count(
                [('experiment_id', '=', record.id)])

    def action_publish(self):
        self.write({'is_published': True})

    def action_published(self):
        return True

    def action_view_experiments(self):
        return True

    def action_count_members(self):
        return True

    @api.model
    def fields_get_queried_keys(self):
        fields = '{id,name,simulab_id,student_experiment_id,simulation_name,members_count,exp_header,preview, summary,objective, description, image_url, grade_id{id,name},subject_id{id,name},completion_time,completion_days,theory_links{id,name,link},theory_details{id,name,description_html,image_url,experiment_info},simulation_stories{id,name,description_html,image_url, experiment_info},theory_techniques{id,name,description_html,image_url, experiment_info},fun_fcts{id,name,description_html,image_url, experiment_info},quiz_ids{id,sequence,name,image_url,question_ids{id,question}}, marks_ids{id,name}, exp_qna{name, description, description_html}},medium_id{id,name}},parent_id'
        return fields

    @api.depends('preview', 'summary', 'objective', 'description', 'fun_fcts', 'theory_links')
    def _compute_experiment_details(self):
        for experiment in self:
            experiment_details = ""
            experiment_details = experiment_details + (
                ('<p><br></p>' + str(experiment.preview)) if not is_html_empty(
                    experiment.preview) else '')
            experiment_details = experiment_details + (
                ('<p><br></p>' + str(experiment.summary)) if not is_html_empty(
                    experiment.summary) else '')
            experiment_details = experiment_details + (
                ('<p><br></p>' + str(experiment.objective)) if not is_html_empty(
                    experiment.objective) else '')
            experiment_details = experiment_details + (
                ('<p><br></p>' + str(experiment.description)) if not is_html_empty(
                    experiment.description) else '')
            experiment.experiment_details = experiment_details + '<p><br></p>' + '<p><br></p>'

    @api.model
    def create(self, values):
        values['simulab_id'] = self.env['ir.sequence'].next_by_code('simulab.content')
        experiment = super().create(values)
        return experiment

    def write(self, values):  
        experiment_relation = ""      
        medium_id = values['medium_id'] if 'medium_id' in values else self.medium_id.id

        existing_experiment = self.env['simulab.experiment'].search(
                [('id', '=',  self.id), ('medium_id', '=', medium_id)])
        if existing_experiment:
            experiment_relation = 'parent'
        
        if not existing_experiment:
            existing_experiment = self.env['simulab.experiment'].search(
                [('parent_id', '=',  self.id), ('medium_id', '=', medium_id)])
            experiment_relation = 'child'
            self = existing_experiment
            
        if existing_experiment:
            #SUBODH:: This is existing record hence update
            if experiment_relation == 'child':
                values['id'] = existing_experiment.id                
            res = super().write(values)
            return res
        else:
            #SUBODH:: This is new record for medium, add parent id
            if self.id:
                values['parent_id'] = self.id
            print(values)                   
            self.create(values)
        # else:
        #     res = super().write(values)
        #     return res

    def _compute_is_new_experiment(self):
        for experiment in self:
            experiment.is_new_experiment = experiment.date_published > fields.Datetime.now() - relativedelta(
                days=7) if experiment.is_published else False

    def _compute_questions_count(self):
        for experiment in self:
            experiment.questions_count = 0

    def _compute_comments_count(self):
        for experiment in self:
            experiment.comments_count = 0

    def _compute_total(self):
        for record in self:
            record.total_views = 0

    def _compute_like_info(self):
        if not self.ids:
            self.update({'likes': 0, 'dislikes': 0})
            return

        rg_data_like = self.env['simulab.experiment.partner'].sudo().read_group(
            [('experiment_id', 'in', self.ids), ('vote', '=', 1)],
            ['experiment_id'], ['experiment_id']
        )
        rg_data_dislike = self.env['simulab.experiment.partner'].sudo().read_group(
            [('experiment_id', 'in', self.ids), ('vote', '=', -1)],
            ['experiment_id'], ['experiment_id']
        )
        mapped_data_like = dict(
            (rg_data['experiment_id'][0], rg_data['experiment_id_count'])
            for rg_data in rg_data_like
        )
        mapped_data_dislike = dict(
            (rg_data['experiment_id'][0], rg_data['experiment_id_count'])
            for rg_data in rg_data_dislike
        )

        for experiment in self:
            experiment.likes = mapped_data_like.get(experiment.id, 0)
            experiment.dislikes = mapped_data_dislike.get(experiment.id, 0)

    def _compute_experiment_views(self):
        # TODO awa: tried compute_sudo, for some reason it doesn't work in here...
        read_group_res = self.env['simulab.experiment.partner'].sudo().read_group(
            [('experiment_id', 'in', self.ids)],
            ['experiment_id'],
            groupby=['experiment_id']
        )
        mapped_data = dict(
            (res['experiment_id'][0], res['experiment_id_count']) for res in read_group_res)
        for experiment in self:
            experiment.experiment_views = mapped_data.get(experiment.id, 0)

    def _compute_experiments_statistics(self):
        # Do not use dict.fromkeys(self.ids, dict()) otherwise it will use the same dictionnary for all keys.
        # Therefore, when updating the dict of one key, it updates the dict of all keys.
        keys = ['nbr_%s' % experiment_type for experiment_type in
                self.env['simulab.experiment']._fields['experiment_type'].get_values(self.env)]
        default_vals = dict((key, 0) for key in keys + ['total_experiments'])

        res = self.env['simulab.experiment'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids),
             ('is_category', '=', False)],
            ['category_id', 'experiment_type'], ['category_id', 'experiment_type'],
            lazy=False)

    def _on_change_url(self):
        self.ensure_one()
        if self.url:
            res = self._parse_document_url(self.url)
            if res.get('error'):
                raise UserError(res.get('error'))
            values = res['values']
            if not values.get('document_id'):
                raise UserError(_('Please enter valid Youtube or Google Doc URL'))
            for key, value in values.items():
                self[key] = value

    def _on_change_datas(self):
        """ For PDFs, we assume that it takes 5 minutes to read a page.
            If the selected file is not a PDF, it is an image (You can
            only upload PDF or Image file) then the experiment_type is changed
            into infographic and the uploaded dataS is transfered to the
            image field. (It avoids the infinite loading in PDF viewer)"""
        if self.datas:
            data = base64.b64decode(self.datas)
            if data.startswith(b'%PDF-'):
                pdf = PyPDF2.PdfFileReader(io.BytesIO(data), overwriteWarnings=False, strict=False)
                try:
                    pdf.getNumPages()
                except PyPDF2.utils.PdfReadError:
                    return
                self.completion_time = (5 * len(pdf.pages)) / 60
            else:
                self.experiment_type = 'infographic'
                self.image_1920 = self.datas
                self.datas = None

    def _compute_can_publish(self):
        for record in self:
            record.can_publish = record.channel_id.can_publish

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """Sets the sequence to zero so that it always lands at the beginning
        of the newly selected course as an uncategorized experiment"""
        rec = super().copy(default)
        rec.sequence = 0
        return rec

    def unlink(self):
        super().unlink()

    def toggle_active(self):
        # archiving/unarchiving a channel does it on its experiments, too
        to_archive = self.filtered(lambda experiment: experiment.active)
        res = super().toggle_active()
        return res

    def action_like(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=True)

    def action_dislike(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=False)

    def _action_vote(self, upvote=True):
        """ Private implementation of voting. It does not check for any real access
        rights; public methods should grant access before calling this method.

          :param upvote: if True, is a like; if False, is a dislike
        """
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['simulab.experiment.partner'].sudo()
        experiment_partners = SlidePartnerSudo.search([
            ('experiment_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id)
        ])
        experiment_id = experiment_partners.mapped('experiment_id')
        new_experiments = self_sudo - experiment_id
        channel = experiment_id.channel_id
        karma_to_add = 0

        for experiment_partner in experiment_partners:
            if upvote:
                new_vote = 0 if experiment_partner.vote == -1 else 1
                if experiment_partner.vote != 1:
                    karma_to_add += channel.karma_gen_experiment_vote
            else:
                new_vote = 0 if experiment_partner.vote == 1 else -1
                if experiment_partner.vote != -1:
                    karma_to_add -= channel.karma_gen_experiment_vote
            experiment_partner.vote = new_vote

        for new_experiment in new_experiments:
            new_vote = 1 if upvote else -1
            new_experiment.write({
                'experiment_partner_ids': [
                    (0, 0, {'vote': new_vote, 'partner_id': self.env.user.partner_id.id})]
            })
            karma_to_add += new_experiment.channel_id.karma_gen_experiment_vote * (
                1 if upvote else -1)

        if karma_to_add:
            self.env.user.add_karma(karma_to_add)

    def action_set_viewed(self, quiz_attempts_inc=False):
        if any(not experiment.channel_id.is_member for experiment in self):
            raise UserError(
                _('You cannot mark a experiment as viewed if you are not among its members.'))

        return bool(
            self._action_set_viewed(self.env.user.partner_id, quiz_attempts_inc=quiz_attempts_inc))

    def _action_set_viewed(self, target_partner, quiz_attempts_inc=False):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['simulab.experiment.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('experiment_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        if quiz_attempts_inc and existing_sudo:
            sql.increment_field_skiplock(existing_sudo, 'quiz_attempts_count')
            SlidePartnerSudo.invalidate_cache(fnames=['quiz_attempts_count'], ids=existing_sudo.ids)

        new_experiments = self_sudo - existing_sudo.mapped('experiment_id')
        return SlidePartnerSudo.create([{
            'experiment_id': new_experiment.id,
            'channel_id': new_experiment.channel_id.id,
            'partner_id': target_partner.id,
            'quiz_attempts_count': 1 if quiz_attempts_inc else 0,
            'vote': 0} for new_experiment in new_experiments])

    def action_set_completed(self):
        if any(not experiment.channel_id.is_member for experiment in self):
            raise UserError(
                _('You cannot mark a experiment as completed if you are not among its members.'))

        return self._action_set_completed(self.env.user.partner_id)

    def _action_set_completed(self, target_partner):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['simulab.experiment.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('experiment_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        existing_sudo.write({'completed': True})

        new_experiments = self_sudo - existing_sudo.mapped('experiment_id')
        SlidePartnerSudo.create([{
            'experiment_id': new_experiment.id,
            'channel_id': new_experiment.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0,
            'completed': True} for new_experiment in new_experiments])

        return True

    def _action_set_quiz_done(self):
        if any(not experiment.channel_id.is_member for experiment in self):
            raise UserError(_(
                'You cannot mark a experiment quiz as completed if you are not among its members.'))

        points = 0
        for experiment in self:
            user_membership_sudo = experiment.user_membership_id.sudo()
            if not user_membership_sudo or user_membership_sudo.completed or not user_membership_sudo.quiz_attempts_count:
                continue

            gains = [experiment.quiz_first_attempt_reward,
                     experiment.quiz_second_attempt_reward,
                     experiment.quiz_third_attempt_reward,
                     experiment.quiz_fourth_attempt_reward]
            points += gains[
                user_membership_sudo.quiz_attempts_count - 1] if user_membership_sudo.quiz_attempts_count <= len(
                gains) else gains[-1]

        return self.env.user.sudo().add_karma(points)

    @api.model
    def _fetch_data(self, base_url, params, content_type=False):
        result = {'values': dict()}
        try:
            response = requests.get(base_url, timeout=3, params=params)
            response.raise_for_status()
            if content_type == 'json':
                result['values'] = response.json()
            elif content_type in ('image', 'pdf'):
                result['values'] = base64.b64encode(response.content)
            else:
                result['values'] = response.content
        except requests.exceptions.HTTPError as e:
            result['error'] = e.response.content
        except requests.exceptions.ConnectionError as e:
            result['error'] = str(e)
        return result

    def _find_document_data_from_url(self, url):
        url_obj = urls.url_parse(url)
        if url_obj.ascii_host == 'youtu.be':
            return ('youtube', url_obj.path[1:] if url_obj.path else False)
        elif url_obj.ascii_host in (
        'youtube.com', 'www.youtube.com', 'm.youtube.com', 'www.youtube-nocookie.com'):
            v_query_value = url_obj.decode_query().get('v')
            if v_query_value:
                return ('youtube', v_query_value)
            split_path = url_obj.path.split('/')
            if len(split_path) >= 3 and split_path[1] in ('v', 'embed'):
                return ('youtube', split_path[2])

        expr = re.compile(
            r'(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)')
        arg = expr.match(url)
        document_id = arg and arg.group(2) or False
        if document_id:
            return ('google', document_id)

        return (None, False)

    def _parse_document_url(self, url, only_preview_fields=False):
        document_source, document_id = self._find_document_data_from_url(url)
        if document_source and hasattr(self, '_parse_%s_document' % document_source):
            return getattr(self, '_parse_%s_document' % document_source)(document_id,
                                                                         only_preview_fields)
        return {'error': _('Unknown document')}

    def get_simulab_experiment(self, params={}):
        medium_id = False
        child_experiment = False
        if 'current_medium_id' in request.session:
            medium_id = int(request.session['current_medium_id'])
       
        course_id = params.get("course_id", False)
        experiment_id = params.get("experiment_id", False)
        enrolled_id = params.get("enrolled_id", False)

        student_experiment = False
        if enrolled_id:
            student_experiment = self.env['student.experiment'].search(
                [('enrolled_course_id', '=', enrolled_id), ('experiment_id', '=', experiment_id)])
            
            if student_experiment:
                student_experiment = student_experiment[0]

        experiment_line = self.env['simulab.experiment.line'].search(
            [('course_id', '=', course_id), ('experiment_id', '=', experiment_id)])
        if not experiment_line:
            return {"message": "Invalid course or experiment"}
        
        experiment_line = experiment_line[0]
        exp_id = experiment_line.experiment_id.id
        simulab_experiment = experiment_line.experiment_id
        #SUBODH :: Get child experiment
        if medium_id != 1:  
            child_experiment = self.env['simulab.experiment'].search(
                [ ('parent_id', '=', experiment_id), ('medium_id', '=', medium_id)])      
       
            if child_experiment:
                simulab_experiment = child_experiment  
                #exp_id = simulab_experiment.id
            else:
                return {"message": "Invalid course or experiment"}
        

        result = {"id": exp_id,
                  "name": simulab_experiment.name,
                  "sequence": experiment_line.sequence,
                  "simulationName": simulab_experiment.simulation_name,
                  "expHeader": simulab_experiment.exp_header,
                  "preview": simulab_experiment.preview,
                  "summary": simulab_experiment.summary,
                  "objective": simulab_experiment.objective,
                  "description": simulab_experiment.description,
                  "imageUrl": simulab_experiment.image_url,
                  "mediumId": {
                      "id": simulab_experiment.medium_id.id,
                      "name": simulab_experiment.medium_id.name
                  },
                  "gradeId": {
                      "id": simulab_experiment.grade_id.id,
                      "name": simulab_experiment.grade_id.name
                  },
                  "subjectId": {
                      "id": simulab_experiment.subject_id.id,
                      "name": simulab_experiment.subject_id.name
                  },
                  "completionTime": simulab_experiment.completion_time,
                  "completionDays": simulab_experiment.completion_days,
                  }

        theory_links = []
        for theory_link in simulab_experiment.theory_links:
            theory_links = theory_links + [
                {"id": theory_link.id, "name": theory_link.name, "link": theory_link.link}]
        result["theoryLinks"] = theory_links

        theory_details = []
        for theory_detail in simulab_experiment.theory_details:
            theory_details = theory_details + [
                {"id": theory_detail.id, "descriptionHtml": theory_detail.description_html,
                 "imageUrl": theory_detail.image_url}]
        result["theoryDetails"] = theory_details

        simulation_stories = []
        for simulation_story in simulab_experiment.simulation_stories:
            simulation_stories = simulation_stories + [
                {"id": simulation_story.id, "descriptionHtml": simulation_story.description_html,
                 "imageUrl": simulation_story.image_url}]
        result["simulationStories"] = simulation_stories

        theory_techniques = []
        for theory_technique in simulab_experiment.theory_techniques:
            theory_techniques = theory_techniques + [
                {"id": theory_technique.id, "descriptionHtml": theory_technique.description_html,
                 "imageUrl": theory_technique.image_url}]
        result["theoryTechniques"] = theory_techniques

        fun_facts = []
        for fun_fact in simulab_experiment.fun_fcts:
            fun_facts = fun_facts + [{"id": fun_fact.id, "name": fun_fact.name,
                                      "descriptionHtml": fun_fact.description_html,
                                      "imageUrl": fun_fact.image_url}]
        result["funFacts"] = fun_facts

        quiz_ids = []
        for quiz_id in simulab_experiment.quiz_ids:
            quiz_ids = quiz_ids + [{"id": quiz_id.id, "name": quiz_id.name}]
        result["experimentQuizzes"] = quiz_ids

        marks_ids = []
        for marks_id in simulab_experiment.marks_ids:
            marks_ids = marks_ids + [{"id": marks_id.id, "name": marks_id.name}]
        result["marksIds"] = marks_ids

        exp_qna = []
        for qna in simulab_experiment.exp_qna:
            exp_qna = exp_qna + [{"description": qna.description, "name": qna.name, "descriptionHTML":qna.description_html}]
        result["expQna"] = exp_qna

        if student_experiment:
            result["studentExperimentId"] = student_experiment.id
            result["status"] = student_experiment.status
            result["simulationProgress"] = student_experiment.simulation_progress
            result["simulationTime"] = student_experiment.simulation_time
            result["simulationDays"] = student_experiment.simulation_days
            result["simulationQuizScore"] = student_experiment.simulation_quiz_score
            result["simulationMilestone"] = student_experiment.simulation_milestone
            result["simulationINIFile"] = student_experiment.simulation_ini_file.id
            result["plannedStartDate"] = student_experiment.planned_start_date
            result["plannedEndDate"] = student_experiment.planned_end_date
            result["status"] = student_experiment.completion_days

        return result
