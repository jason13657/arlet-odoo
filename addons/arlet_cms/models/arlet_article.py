from odoo import models, fields, api
from .utils import split_lines, slugify, WEB_BASE


class ArletProfile(models.Model):
    _name = 'arlet.profile'
    _description = 'Arlet Profile'
    _rec_name = 'title'
    _inherit = ['arlet.translatable.mixin']

    name = fields.Char(string='Internal Name', required=True)
    title = fields.Char(string='Full Name', required=True)
    label = fields.Char(string='Role / Title')
    # EN base values
    html = fields.Html(string='Bio')
    list_label = fields.Char(string='Certifications Label')
    list_items = fields.Text(string='Certifications — one per line')
    image = fields.Image(string='Photo', max_width=0, max_height=0)
    image_alt = fields.Char(string='Photo Alt')
    image_caption = fields.Char(string='Photo Caption')
    hero_bg = fields.Image(
        string='Host Page Hero BG',
        max_width=0, max_height=0,
        help='Full-width background image shown at the top of this host\'s events page (e.g. /events/host/<slug>). '
             'Falls back to the profile photo when not set.',
    )
    hero_bg_alt = fields.Char(string='Host Page Hero BG Alt')
    slug = fields.Char(
        string='Slug',
        compute='_compute_slug', store=True, readonly=True,
        help='Auto-generated from the Internal Name.',
    )
    link_ids = fields.One2many('arlet.profile.link', 'profile_id', string='Links')
    translation_ids = fields.One2many('arlet.profile.translation', 'profile_id', string='Translations')

    _slug_unique = models.Constraint('UNIQUE(slug)', 'A profile with this slug already exists.')

    @api.depends('name')
    def _compute_slug(self):
        for rec in self:
            rec.slug = slugify(rec.name or '')

    def to_api_dict(self, locale='en'):
        return {
            'slug': self.slug or '',
            'title': self.title or '',
            'label': self.label or '',
            'html': self._t('html', locale),
            'listLabel': self._t('list_label', locale),
            'listItems': split_lines(self._t('list_items', locale)),
            'image': self._img_url('image'),
            'imageAlt': self.image_alt or '',
            'imageCaption': self.image_caption or '',
            'heroBg': self._img_url('hero_bg'),
            'heroBgAlt': self.hero_bg_alt or '',
            'links': [link.to_api_dict() for link in self.link_ids],
        }


class ArletProfileTranslation(models.Model):
    _name = 'arlet.profile.translation'
    _description = 'Profile Translation'
    _inherit = ['arlet.base.translation']

    profile_id = fields.Many2one('arlet.profile', required=True, ondelete='cascade')
    html = fields.Html(string='Bio')
    list_label = fields.Char(string='Certifications Label')
    list_items = fields.Text(string='Certifications — one per line')

    _locale_profile_unique = models.Constraint('UNIQUE(profile_id, locale)', 'A translation for this locale already exists for this profile.')


class ArletProfileLink(models.Model):
    _name = 'arlet.profile.link'
    _description = 'Profile Link'
    _order = 'sequence asc'

    profile_id = fields.Many2one('arlet.profile', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True, help='e.g. "Instagram"')
    value = fields.Char(required=True, help='e.g. "@aminluc"')
    href = fields.Char(help='URL. Leave empty to render value as plain text.')

    def to_api_dict(self):
        data = {'label': self.label or '', 'value': self.value or ''}
        if self.href:
            data['href'] = self.href
        return data


class ArletContentBlock(models.Model):
    _name = 'arlet.content.block'
    _description = 'Article Content Block'
    _order = 'sequence asc'
    _inherit = ['arlet.translatable.mixin']

    article_id = fields.Many2one('arlet.article', ondelete='cascade')
    event_article_id = fields.Many2one('arlet.event', ondelete='cascade')
    location_article_id = fields.Many2one('arlet.location', ondelete='cascade')
    sequence = fields.Integer(default=10)
    type = fields.Selection([
        ('cover',    'Cover — full-width bg image + text'),
        ('split',    'Split — image + text side by side'),
        ('half',     'Half — two-column text only'),
        ('text',     'Text — single column (center / left)'),
        ('image',    'Image — full-width, no text'),
        ('occasion', 'Occasion — two-column list'),
        ('profile',  'Profile — single person card'),
        ('profiles', 'Profiles — grid of person cards'),
        ('testimonial', 'Testimonial — quote with optional image'),
        ('location', 'Location — image + description'),
        ('program',  'Program — event schedule grid'),
        ('form',     'Form — embedded HubSpot form'),
    ], string='Block Type', required=True)

    # Image / background
    bg_image = fields.Image(string='BG Image', max_width=0, max_height=0, help='Used for type=cover')
    image = fields.Image(string='Image', max_width=0, max_height=0, help='Used for type=split')
    image_alt = fields.Char(string='Image Alt')
    image_position = fields.Selection(
        [('left', 'Left'), ('right', 'Right')], string='Image Position',
    )
    image_padding = fields.Selection([
        ('small',  'Small'),
        ('medium', 'Medium'),
        ('large',  'Large'),
    ], string='Image Padding', help='Insets the image from the section edge. Applies to type=split and type=location.')

    # Styling
    bg = fields.Selection([
        ('black', 'Black'), ('white', 'White'), ('bg', 'BG'),
        ('grey-light', 'Grey Light'), ('grey-mid', 'Grey Mid'), ('grey-dark', 'Grey Dark'),
    ], string='Background')
    text_color = fields.Selection(
        [('black', 'Black'), ('white', 'White')], string='Text Color',
    )
    padding_y = fields.Selection([
        ('small',  'Small'),
        ('medium', 'Medium'),
        ('large',  'Large'),
    ], string='Padding Y')
    text_align = fields.Selection([
        ('center', 'Center (max-width)'),
        ('left',   'Left'),
    ], string='Text Align', default='center')
    padding_x = fields.Selection([
        ('small',  'Small'),
        ('medium', 'Medium'),
        ('large',  'Large'),
    ], string='Padding X')

    # EN base text values
    title = fields.Char(string='Title')
    label = fields.Char(string='Label')
    subtitle = fields.Char(string='Subtitle')
    html = fields.Html(string='Body HTML')
    paragraphs = fields.Text(string='Paragraphs — one per line (used if HTML absent)')
    footer = fields.Text(string='Footer Lines — one per line')
    left_items = fields.Text(string='Left Items — one per line (type=occasion)')
    right_items = fields.Text(string='Right Items — one per line (type=occasion)')

    # Relations
    profile_id = fields.Many2one('arlet.profile', string='Profile', help='Required for type=profile')
    profile_ids = fields.Many2many(
        'arlet.profile',
        'arlet_content_block_profile_rel',
        'block_id', 'profile_id',
        string='Profiles',
        help='Required for type=profiles',
    )
    location_id = fields.Many2one('arlet.location', string='Location', help='Required for type=location')
    event_id = fields.Many2one('arlet.event', string='Event', help='Required for type=program')
    hubspot_form_id = fields.Many2one('arlet.hubspot.form', string='HubSpot Form', help='Required for type=form')
    translation_ids = fields.One2many('arlet.content.block.translation', 'block_id', string='Translations')

    def to_api_dict(self, locale='en'):
        data = {'type': self.type}

        for attr, key in [
            ('image_alt', 'imageAlt'),
            ('image_position', 'imagePosition'), ('image_padding', 'imagePadding'), ('bg', 'bg'), ('text_color', 'textColor'),
            ('padding_y', 'paddingY'), ('padding_x', 'paddingX'), ('text_align', 'textAlign'),
        ]:
            val = getattr(self, attr, None)
            if val:
                data[key] = val
        for attr, key in [('bg_image', 'bgImage'), ('image', 'image')]:
            url = self._img_url(attr)
            if url:
                data[key] = url

        for field_name, key in [
            ('title', 'title'), ('label', 'label'), ('subtitle', 'subtitle'),
        ]:
            val = self._t(field_name, locale)
            if val:
                data[key] = val

        # html takes priority over paragraphs
        html = self._t('html', locale)
        if html:
            data['html'] = html
        else:
            paragraphs = split_lines(self._t('paragraphs', locale))
            if paragraphs:
                data['paragraphs'] = paragraphs

        footer = split_lines(self._t('footer', locale))
        if footer:
            data['footer'] = footer

        left_items = split_lines(self._t('left_items', locale))
        if left_items:
            data['leftItems'] = left_items

        right_items = split_lines(self._t('right_items', locale))
        if right_items:
            data['rightItems'] = right_items

        if self.profile_id:
            data['profile'] = self.profile_id.to_api_dict(locale)
            # For testimonial blocks, auto-fill display fields from the linked profile
            # when the raw text fields have not been overridden manually.
            if self.type == 'testimonial':
                if not data.get('title'):
                    data['title'] = self.profile_id.title or ''
                if not data.get('subtitle'):
                    data['subtitle'] = self.profile_id.label or ''
                if not data.get('image'):
                    data['image'] = self.profile_id._img_url('image')
                if not data.get('imageAlt'):
                    data['imageAlt'] = self.profile_id.image_alt or ''
        if self.profile_ids:
            data['profiles'] = [p.to_api_dict(locale) for p in self.profile_ids]
        if self.location_id:
            data['location'] = self.location_id.to_api_dict(locale)
        if self.event_id:
            data['event'] = self.event_id.to_api_dict(locale)
        if self.hubspot_form_id:
            data['formPortalId'] = self.hubspot_form_id.portal_id or ''
            data['formGuid'] = self.hubspot_form_id.guid or ''
            data['formFields'] = self.hubspot_form_id.fields_json or []
        return data


class ArletContentBlockTranslation(models.Model):
    _name = 'arlet.content.block.translation'
    _description = 'Content Block Translation'
    _inherit = ['arlet.base.translation']

    block_id = fields.Many2one('arlet.content.block', required=True, ondelete='cascade')
    block_type = fields.Selection(related='block_id.type', string='Block Type', store=False)
    title = fields.Char(string='Title')
    label = fields.Char(string='Label')
    subtitle = fields.Char(string='Subtitle')
    html = fields.Html(string='Body HTML')
    paragraphs = fields.Text(string='Paragraphs — one per line')
    footer = fields.Text(string='Footer Lines — one per line')
    left_items = fields.Text(string='Left Items — one per line')
    right_items = fields.Text(string='Right Items — one per line')

    _locale_block_unique = models.Constraint('UNIQUE(block_id, locale)', 'A translation for this locale already exists for this block.')


class ArletArticle(models.Model):
    _name = 'arlet.article'
    _description = 'Arlet Article'
    _order = 'status desc, published_at desc'
    _inherit = ['arlet.translatable.mixin']

    name = fields.Char(string='Internal Name', required=True)
    # EN base values
    badge = fields.Char(string='Badge', required=True)
    title = fields.Char(string='Title', required=True)
    subtitle = fields.Char(string='Subtitle')
    description = fields.Text(string='Description / Excerpt')
    intro = fields.Text(string='Intro Paragraphs — one per line')
    published_at = fields.Date(string='Published At', required=True)
    author = fields.Char()
    location = fields.Char()
    image = fields.Image(string='Cover Image', max_width=0, max_height=0, required=True)
    slug = fields.Char(
        string='Slug',
        compute='_compute_slug', store=True, readonly=True,
        help='Auto-generated from the Internal Name.',
    )
    status = fields.Selection(
        [('published', 'Published'), ('draft', 'Draft')],
        required=True,
        default='draft',
    )
    section = fields.Selection(
        [('read_arlet', 'Read Arlet'), ('press_media', 'Press & Media')],
        string='Section',
        required=True,
        default='read_arlet',
    )
    featured = fields.Boolean(string='Featured', default=False)
    # Detail page
    hero_bg = fields.Image(string='Hero BG', max_width=0, max_height=0)
    hero_bg_alt = fields.Char(string='Hero BG Alt')
    content_ids = fields.One2many('arlet.content.block', 'article_id', string='Content Blocks')
    translation_ids = fields.One2many('arlet.article.translation', 'article_id', string='Translations')

    _slug_unique = models.Constraint('UNIQUE(slug)', 'An article with this slug already exists.')

    @api.depends('name')
    def _compute_slug(self):
        for rec in self:
            rec.slug = slugify(rec.name or '')

    def _base_dict(self, locale='en'):
        return {
            'id': str(self.id),
            'badge': self._t('badge', locale),
            'title': self._t('title', locale),
            'subtitle': self._t('subtitle', locale),
            'publishedAt': self.published_at.isoformat() if self.published_at else '',
            'author': self.author or '',
            'location': self.location or '',
            'description': self._t('description', locale),
            'image': self._img_url('image'),
            'slug': self.slug or '',
            'status': self.status,
            'section': self.section or 'read_arlet',
            'featured': self.featured,
        }

    def to_list_api_dict(self, locale='en'):
        return self._base_dict(locale)

    def to_detail_api_dict(self, locale='en'):
        data = self._base_dict(locale)
        data.update({
            'heroBg': self._img_url('hero_bg'),
            'heroBgAlt': self.hero_bg_alt or '',
            'intro': split_lines(self._t('intro', locale)),
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
            'url': f'{WEB_BASE}/en/staff/preview/article/{self.slug}',
            'target': 'new',
        }


class ArletArticleTranslation(models.Model):
    _name = 'arlet.article.translation'
    _description = 'Article Translation'
    _inherit = ['arlet.base.translation']

    article_id = fields.Many2one('arlet.article', required=True, ondelete='cascade')
    badge = fields.Char(string='Badge')
    title = fields.Char(string='Title')
    subtitle = fields.Char(string='Subtitle')
    description = fields.Text(string='Description / Excerpt')
    intro = fields.Text(string='Intro Paragraphs — one per line')

    _locale_article_unique = models.Constraint('UNIQUE(article_id, locale)', 'A translation for this locale already exists for this article.')
