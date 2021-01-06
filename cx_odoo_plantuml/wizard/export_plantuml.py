###################################################################################
# 
#    Copyright (C) 2020 Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from base64 import b64encode

from odoo import models, fields, api, _
from odoo.exceptions import MissingError

from ..models.link_generator import get_url

PREVIEW_HTML = "<h3 style='text-align:center;'>Preview only!<br/>Download source code for details</h3><p>" \
               "<a href='{}/{}' target='_blank'>" \
               "<img style='max-width:95%;height:auto' src='http://www.plantuml.com/plantuml/png/{}'></img>" \
               "</a></p>"
INSTALLED = ['installed', 'to upgrade', 'uninstallable']


##############
# Export UML #
##############
class ShowUML(models.TransientModel):
    _name = "cx.plantuml.export.wiz"
    _description = "PlantUML Export Wizard"

    module_id = fields.Many2one(string="Module",
                                comodel_name="ir.module.module",
                                default=lambda self: self._context["active_id"])
    installed = fields.Boolean(string="Installed",
                               compute="_compute_installed")
    deps = fields.Binary(string="Dependencies",
                         attachment=False)   # Do not use attachments for storage
    deps_fname = fields.Char(string="Dependencies")
    deps_preview = fields.Html(string="Preview")
    models = fields.Binary(string="Module Models",
                           attachment=False)
    models_fname = fields.Char(string="Module Models")
    models_preview = fields.Html(string="Preview")
    show_fields = fields.Boolean(string="Export Model Fields",
                                 help="Show model fields on schema")
    show_inherited = fields.Boolean(string="Export Inherited Fields",
                                    help="Show already existing fields for inherited models.\n"
                                         "May result is significant schema growth!")

    # -- Show Pro warning
    @api.onchange("show_fields", "show_inherited")
    def show_pro_warning(self):
        if self.module_id:
            if not self.show_fields:
                self.show_inherited = False
            elif self.show_inherited or self.show_fields:
                raise MissingError(_("Please purchase Pro version to use this feature!"))

    # -- If module is installed
    @api.depends("module_id")
    def _compute_installed(self):
        for rec in self:
            if rec.module_id and rec.module_id.state in INSTALLED:
                rec.installed = True
            else:
                rec.installed = False

    @api.onchange("module_id", "show_fields", "show_inherited")
    def module_id_change(self):
        if self.module_id:
            server = self.env['ir.config_parameter'].sudo(). \
                get_param("cx_odoo_plantuml.cetmix_plantuml_server_url", False)
            deps, modules_found = self.module_id.get_uml_deps()
            vals = {
                "deps": b64encode(deps.encode("utf-8")),
                "deps_fname": "_".join((self.module_id.name, "deps.puml"))
            }
            # Compose preview
            if server:
                url = get_url(deps)
                vals.update(
                    {
                        "deps_preview": PREVIEW_HTML.format(server, url, url),
                    }
                )

            # Add models data
            if self.installed:
                if self.show_inherited:
                    show_fields = "inherited"
                elif self.show_fields:
                    show_fields = "fields"
                else:
                    show_fields = False
                mods = self.module_id.with_context(show_fields=show_fields).get_uml_models(modules_found)
                mods_pro = self.module_id.with_context(show_fields=show_fields).get_uml_models(modules_found,
                                                                                               pro=True)
                vals.update(
                    {
                        "models": b64encode(mods_pro.encode("utf-8")),
                        "models_fname": "_".join((self.module_id.name, "models.puml"))
                    }
                )
                # Compose preview
                if server:
                    url = get_url(mods)
                    vals.update(
                        {
                            "models_preview": PREVIEW_HTML.format(server, url, url),
                        }
                    )

            self.update(vals)

