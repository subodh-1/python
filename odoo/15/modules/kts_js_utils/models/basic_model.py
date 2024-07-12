# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def on_cick_statusbar_stage(self, record_id, data_changed):
        print(record_id)
        """ 
            :param self: current model.
                   record_id: id of record if save on write function, False on create function
                   data_changed: data changed on form
            :returns: True: show dialog
                      False: ignore dialog
        """
        return False
