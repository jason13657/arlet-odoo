import os

from odoo import http
from odoo.http import request

# ---------------------------------------------------------------------------
# Configuration — set these environment variables before starting Odoo.
#
#   ARLET_CORS_ORIGIN   Allowed CORS origin, e.g. "https://arlet.com"
#                       Defaults to "*" (open) when not set.
#
#   ARLET_API_KEY       Shared secret. When set, every request must include:
#                           X-Api-Key: <value>
#                       Leave unset (or empty) to disable key enforcement.
# ---------------------------------------------------------------------------
_CORS = os.environ.get('ARLET_CORS_ORIGIN', '*')
_API_KEY = os.environ.get('ARLET_API_KEY', '')
_VALID_LOCALES = ('en', 'fr')


class ArletApiController(http.Controller):

    def _check_api_key(self):
        """Return a 401 JSON response if the API key is wrong, else None."""
        if not _API_KEY:
            return None
        provided = request.httprequest.headers.get('X-Api-Key', '')
        if provided != _API_KEY:
            return request.make_json_response({'error': 'Unauthorized'}, status=401)
        return None

    # ------------------------------------------------------------------
    # GET /api/arlet/page-config/<page_key>?locale=en
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/page-config/<string:page_key>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def get_page_config(self, page_key, locale='en', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        config = request.env['arlet.page.config'].sudo().search(
            [('page_key', '=', page_key)], limit=1,
        )
        if not config:
            return request.make_json_response({'pageKey': page_key})
        return request.make_json_response(config.to_api_dict(locale))

    # ------------------------------------------------------------------
    # GET /api/arlet/events?locale=en
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/events',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def list_events(self, locale='en', owner_slug='', q='', page='', limit='12', status='all', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        domain = []
        if owner_slug:
            domain += [('owner_id.slug', '=', owner_slug)]
        if q:
            domain += [('title', 'ilike', q)]
        from datetime import date
        today = date.today().isoformat()
        if status == 'upcoming':
            domain += ['|', ('start_date', '>=', today), ('start_date', '=', False)]
        elif status == 'archived':
            domain += [('start_date', '<', today)]
        all_events = request.env['arlet.event'].sudo().search(domain)
        # Sort: dated events first (asc), undated events last
        def sort_key(e):
            return (0, e.start_date.isoformat()) if e.start_date else (1, '')
        all_events = sorted(all_events, key=sort_key)
        # Paginate when page param is provided
        if page:
            try:
                page_num = max(1, int(page))
                page_size = max(1, int(limit))
            except (ValueError, TypeError):
                page_num, page_size = 1, 12
            total = len(all_events)
            import math
            pages = math.ceil(total / page_size) if page_size else 1
            offset = (page_num - 1) * page_size
            paged = all_events[offset:offset + page_size]
            data = [e.to_api_dict(locale) for e in paged]
            return request.make_json_response({
                'items': data,
                'total': total,
                'page': page_num,
                'limit': page_size,
                'pages': pages,
            })
        data = [e.to_api_dict(locale) for e in all_events]
        return request.make_json_response(data)

    # ------------------------------------------------------------------
    # GET /api/arlet/articles?locale=en
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/articles',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def list_articles(self, locale='en', q='', page='', limit='12', featured='', section='', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        domain = []
        if q:
            domain += [('title', 'ilike', q)]
        if featured == 'true':
            domain += [('featured', '=', True)]
        if section in ('read_arlet', 'press_media'):
            domain += [('section', '=', section)]
        all_articles = request.env['arlet.article'].sudo().search(domain)
        # Paginate when page param is provided
        if page:
            try:
                page_num = max(1, int(page))
                page_size = max(1, int(limit))
            except (ValueError, TypeError):
                page_num, page_size = 1, 12
            total = len(all_articles)
            import math
            pages = math.ceil(total / page_size) if page_size else 1
            offset = (page_num - 1) * page_size
            paged = all_articles[offset:offset + page_size]
            data = [a.to_list_api_dict(locale) for a in paged]
            return request.make_json_response({
                'items': data,
                'total': total,
                'page': page_num,
                'limit': page_size,
                'pages': pages,
            })
        data = [a.to_list_api_dict(locale) for a in all_articles]
        return request.make_json_response(data)

    # ------------------------------------------------------------------
    # GET /api/arlet/articles/<slug>?locale=en
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/articles/<string:slug>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def get_article_by_slug(self, slug, locale='en', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        article = request.env['arlet.article'].sudo().search(
            [('slug', '=', slug), ('status', '=', 'published')],
            limit=1,
        )
        if not article:
            return request.make_json_response(None, status=404)
        return request.make_json_response(article.to_detail_api_dict(locale))

    # ------------------------------------------------------------------
    # GET /api/arlet/articles/preview/<slug>?locale=en  (draft allowed)
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/articles/preview/<string:slug>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def get_article_preview(self, slug, locale='en', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        article = request.env['arlet.article'].sudo().search(
            [('slug', '=', slug)],
            limit=1,
        )
        if not article:
            return request.make_json_response(None, status=404)
        return request.make_json_response(article.to_detail_api_dict(locale))

    # ------------------------------------------------------------------
    # GET /api/arlet/locales
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/locales',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def list_locales(self, **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locales = request.env['arlet.locale'].sudo().search([], order='code asc')
        # Always prepend EN (the base language — not stored in arlet.locale)
        data = [{'code': 'en', 'name': 'English'}] + [
            {'code': loc.code, 'name': loc.name} for loc in locales
        ]
        return request.make_json_response(data)

    # ------------------------------------------------------------------
    # GET /api/arlet/locations
    # ------------------------------------------------------------------
    # GET /api/arlet/events/<slug>?locale=en
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/events/<string:slug>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def get_event_by_slug(self, slug, locale='en', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        event = request.env['arlet.event'].sudo().search(
            [('slug', '=', slug)],
            limit=1,
        )
        if not event:
            return request.make_json_response(None, status=404)
        return request.make_json_response(event.to_detail_api_dict(locale))

    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/locations',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def list_locations(self, **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locations = request.env['arlet.location'].sudo().search([])
        data = [loc.to_list_api_dict() for loc in locations]
        return request.make_json_response(data)

    # ------------------------------------------------------------------
    # GET /api/arlet/locations/<slug>?locale=en
    # ------------------------------------------------------------------
    @http.route(
        '/api/arlet/locations/<string:slug>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors=_CORS,
    )
    def get_location_by_slug(self, slug, locale='en', **kwargs):
        err = self._check_api_key()
        if err:
            return err
        locale = locale if locale in _VALID_LOCALES else 'en'
        location = request.env['arlet.location'].sudo().search(
            [('slug', '=', slug)],
            limit=1,
        )
        if not location:
            return request.make_json_response(None, status=404)
        return request.make_json_response(location.to_detail_api_dict(locale))
