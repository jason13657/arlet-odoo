from odoo import models, fields, api
from .utils import slugify, WEB_BASE


class ArletEvent(models.Model):
    _name = 'arlet.event'
    _description = 'Arlet Event'
    _order = 'start_date asc'
    _inherit = ['arlet.translatable.mixin']

    name = fields.Char(string='Internal Name', required=True)
    category = fields.Many2one(
        'arlet.event.category',
        string='Category',
        ondelete='restrict',
    )
    # EN base values (used as fallback when translation is missing)
    title = fields.Char(string='Title', required=True)
    subtitle = fields.Char(string='Subtitle')
    location = fields.Char(string='Location')
    description = fields.Text(string='Description')
    image = fields.Image(string='Image', max_width=0, max_height=0)
    slug = fields.Char(
        string='Slug',
        compute='_compute_slug', store=True, readonly=True,
        help='Auto-generated from the Internal Name.',
    )
    coming_soon = fields.Boolean(string='Coming Soon', default=False)
    featured = fields.Boolean(string='Featured', default=False)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    period = fields.Char(string='Period', help='Free-text period label (e.g. "Summer 2026"). Shown instead of dates when set.')
    program_ids = fields.One2many('arlet.event.program.day', 'event_id', string='Program')
    # Event owner / host (e.g. a partner brand)
    owner_id = fields.Many2one(
        'arlet.profile',
        string='Event Owner / Host',
        ondelete='set null',
        help='The person or brand that commissioned / co-hosts this event. Enables the "See X\'s events" CTA.',
    )
    # Detail page
    hero_bg = fields.Image(string='Hero BG', max_width=0, max_height=0)
    hero_bg_alt = fields.Char(string='Hero BG Alt')
    content_ids = fields.One2many('arlet.content.block', 'event_article_id', string='Content Blocks')
    translation_ids = fields.One2many('arlet.event.translation', 'event_id', string='Translations')

    _slug_unique = models.Constraint('UNIQUE(slug)', 'An event with this slug already exists.')

    @api.depends('name')
    def _compute_slug(self):
        for rec in self:
            rec.slug = slugify(rec.name or '')

    def _base_dict(self, locale='en'):
        data = {
            'id': str(self.id),
            'category': self.category.name if self.category else '',
            'categoryKey': self.category.key if self.category else '',
            'title': self._t('title', locale),
            'subtitle': self._t('subtitle', locale),
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'period': self.period or None,
            'location': self._t('location', locale),
            'description': self._t('description', locale),
            'image': self._img_url('image'),
            'slug': self.slug or '',
            'comingSoon': self.coming_soon,
            'featured': self.featured,
        }
        if self.owner_id:
            data['owner'] = {
                'slug': self.owner_id.slug or '',
                'title': self.owner_id.title or '',
                'label': self.owner_id.label or '',
                'image': self.owner_id._img_url('image'),
                'heroBg': self.owner_id._img_url('hero_bg'),
                'heroBgAlt': self.owner_id.hero_bg_alt or '',
            }
        return data

    def to_api_dict(self, locale='en'):
        data = self._base_dict(locale)
        if self.program_ids:
            data['program'] = [day.to_api_dict(locale) for day in self.program_ids]
        return data

    def to_detail_api_dict(self, locale='en'):
        data = self._base_dict(locale)
        if self.program_ids:
            data['program'] = [day.to_api_dict(locale) for day in self.program_ids]
        data.update({
            'heroBg': self._img_url('hero_bg'),
            'heroBgAlt': self.hero_bg_alt or '',
            'content': [block.to_api_dict(locale) for block in self.content_ids],
        })
        return data

    def action_preview(self):
        self.ensure_one()
        if not self.slug:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Set a slug first to enable preview.',
                    'type': 'warning',
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'url': f'{WEB_BASE}/en/staff/preview/event/{self.slug}',
            'target': 'new',
        }


class ArletEventTranslation(models.Model):
    _name = 'arlet.event.translation'
    _description = 'Event Translation'
    _inherit = ['arlet.base.translation']

    event_id = fields.Many2one('arlet.event', required=True, ondelete='cascade')
    title = fields.Char(string='Title')
    subtitle = fields.Char(string='Subtitle')
    location = fields.Char(string='Location')
    description = fields.Text(string='Description')

    _locale_event_unique = models.Constraint('UNIQUE(event_id, locale)', 'A translation for this locale already exists for this event.')


class ArletEventProgramDay(models.Model):
    _name = 'arlet.event.program.day'
    _description = 'Event Program Day'
    _order = 'sequence asc'
    _rec_name = 'date_label'
    _inherit = ['arlet.translatable.mixin']

    event_id = fields.Many2one('arlet.event', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    date_label = fields.Char(
        string='Date Label', required=True,
        help='Human-readable, e.g. "Friday, July 17th 2025"',
    )
    theme = fields.Char(string='Day Theme', help='e.g. "Gentle Arrival"')
    slot_ids = fields.One2many('arlet.event.program.slot', 'day_id', string='Slots')
    translation_ids = fields.One2many(
        'arlet.event.program.day.translation', 'day_id', string='Translations',
    )

    def to_api_dict(self, locale='en'):
        data = {
            'date': self._t('date_label', locale),
            'slots': [slot.to_api_dict(locale) for slot in self.slot_ids],
        }
        theme = self._t('theme', locale)
        if theme:
            data['theme'] = theme
        return data


class ArletEventProgramDayTranslation(models.Model):
    _name = 'arlet.event.program.day.translation'
    _description = 'Program Day Translation'
    _inherit = ['arlet.base.translation']

    day_id = fields.Many2one('arlet.event.program.day', required=True, ondelete='cascade')
    date_label = fields.Char(string='Date Label')
    theme = fields.Char(string='Day Theme')

    _locale_day_unique = models.Constraint('UNIQUE(day_id, locale)', 'A translation for this locale already exists for this day.')


class ArletEventProgramSlot(models.Model):
    _name = 'arlet.event.program.slot'
    _description = 'Event Program Slot'
    _order = 'sequence asc'
    _rec_name = 'start_at'
    _inherit = ['arlet.translatable.mixin']

    day_id = fields.Many2one('arlet.event.program.day', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    start_at = fields.Char(string='Start At', required=True, help='e.g. "7.45 AM"')
    end_at = fields.Char(string='End At', help='e.g. "10.00 AM". Leave empty for single-point.')
    activity = fields.Char(string='Activity', required=True)
    translation_ids = fields.One2many(
        'arlet.event.program.slot.translation', 'slot_id', string='Translations',
    )

    def to_api_dict(self, locale='en'):
        data = {
            'startAt': self.start_at or '',
            'activity': self._t('activity', locale),
        }
        if self.end_at:
            data['endAt'] = self.end_at
        return data


class ArletEventProgramSlotTranslation(models.Model):
    _name = 'arlet.event.program.slot.translation'
    _description = 'Program Slot Translation'
    _inherit = ['arlet.base.translation']

    slot_id = fields.Many2one('arlet.event.program.slot', required=True, ondelete='cascade')
    activity = fields.Char(string='Activity')

    _locale_slot_unique = models.Constraint('UNIQUE(slot_id, locale)', 'A translation for this locale already exists for this slot.')
