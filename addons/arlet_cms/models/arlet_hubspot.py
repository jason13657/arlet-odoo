import logging
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ArletHubspotForm(models.Model):
    _name = 'arlet.hubspot.form'
    _description = 'HubSpot Form (synced cache)'
    _rec_name = 'name'
    _order = 'name asc'

    portal_id = fields.Char(string='Portal ID', readonly=True)
    guid = fields.Char(string='Form GUID', required=True, readonly=True)
    name = fields.Char(string='Form Name', required=True, readonly=True)
    fields_json = fields.Json(string='Fields', readonly=True)
    raw_json = fields.Json(string='Raw HubSpot Payload', readonly=True)

    _guid_unique = models.Constraint('UNIQUE(guid)', 'A form with this GUID already exists.')

    @api.model
    def _get_api_key(self):
        key = self.env['ir.config_parameter'].sudo().get_param('arlet.hubspot.api_key', '')
        if not key:
            raise UserError(
                'HubSpot API key is not configured. '
                'Go to Settings → Technical → System Parameters and set arlet.hubspot.api_key.'
            )
        return key

    @api.model
    def sync_from_hubspot(self):
        """Fetch all forms from HubSpot and upsert into this model (batch)."""
        _logger.info('HubSpot sync: started')
        api_key = self._get_api_key()
        headers = {'Authorization': f'Bearer {api_key}'}

        # Fetch portal ID from account info
        _logger.info('HubSpot sync: fetching account info')
        account_resp = requests.get(
            'https://api.hubapi.com/account-info/v3/details',
            headers=headers, timeout=15,
        )
        if not account_resp.ok:
            _logger.error('HubSpot sync: account-info error %s — %s', account_resp.status_code, account_resp.text)
            raise UserError(f'HubSpot account-info error {account_resp.status_code}: {account_resp.text}')
        portal_id = str(account_resp.json().get('portalId', '') or '')
        _logger.info('HubSpot sync: portal_id=%s', portal_id)

        # Paginate through all HubSpot forms
        url = 'https://api.hubapi.com/marketing/v3/forms/'
        all_forms = []
        after = None
        page = 1
        while True:
            params = {'limit': 50}
            if after:
                params['after'] = after
            _logger.info('HubSpot sync: fetching forms page %d', page)
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if not resp.ok:
                _logger.error('HubSpot sync: forms API error %s — %s', resp.status_code, resp.text)
                raise UserError(f'HubSpot API error {resp.status_code}: {resp.text}')
            body = resp.json()
            batch = body.get('results', [])
            all_forms.extend(batch)
            _logger.info('HubSpot sync: page %d — %d forms (total so far: %d)', page, len(batch), len(all_forms))
            after = (body.get('paging') or {}).get('next', {}).get('after')
            if not after:
                break
            page += 1

        _logger.info('HubSpot sync: %d total forms fetched, building upsert payload', len(all_forms))

        # Build lookup of inbound data keyed by guid
        incoming = {}
        for form in all_forms:
            guid = form.get('id', '')
            if not guid:
                continue
            incoming[guid] = {
                'guid': guid,
                'portal_id': portal_id,
                'name': form.get('name', guid),
                'raw_json': form,
                'fields_json': [
                    {
                        'name': f.get('name', ''),
                        'label': f.get('label', ''),
                        'placeholder': f.get('placeholder', ''),
                        'required': f.get('required', False),
                        'fieldType': f.get('fieldType', 'single_line_text'),
                    }
                    for group in form.get('fieldGroups', [])
                    for f in group.get('fields', [])
                    if not f.get('hidden')
                ],
            }

        # Single query to fetch all existing records
        existing_recs = self.search([('guid', 'in', list(incoming.keys()))])
        existing_by_guid = {r.guid: r for r in existing_recs}
        _logger.info('HubSpot sync: %d existing records found in DB', len(existing_by_guid))

        # Batch write existing, batch create new
        to_create = []
        for guid, vals in incoming.items():
            if guid in existing_by_guid:
                existing_by_guid[guid].write(vals)
            else:
                to_create.append(vals)
        if to_create:
            self.create(to_create)
            _logger.info('HubSpot sync: created %d new records', len(to_create))

        updated = len(incoming) - len(to_create)
        _logger.info('HubSpot sync: done — %d updated, %d created', updated, len(to_create))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'HubSpot Sync',
                'message': f'{len(incoming)} form(s) synced successfully.',
                'sticky': False,
                'type': 'success',
            },
        }
