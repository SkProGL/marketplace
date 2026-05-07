from datetime import date, timedelta
from django.apps import AppConfig
from django.db import models
from django.contrib import messages
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.utils import timezone
from typing import Type, Any
from django.forms import modelform_factory
from django.utils.html import format_html
from django.http import HttpRequest
from core.forms import PASSWORD_STRENGTH_ERROR, SignupForm
from core.models import Order, Product, ProductBatch
from django.core.cache import cache
import requests
import math
from decimal import Decimal

# Management
## Universal readonly fields
READONLY_FIELDS = ['id', 'date_joined', 'last_login']
## Producer specific fields
PRODUCER_ID_FIELDS = {'Product': 'producer', 'StoryPost': 'user', 'Recipe': 'user'}
## Fields to show first, per model
MODEL_FIELD_PRIORITY = {
    'User': ['email', 'password', 'full_name', 'category', 'organisation_name','phone', 'addrss', 'postcode^'],
    'Product': ['name', 'category', 'price', 'stock_alert_threshold', 'all_year', 'seasonStart', 'seasonEnd'],
    'ProductBatch': ['product', 'quality_class', 'stock', 'stock_alert_threshold', 'availability', 'best_before'],
    'Order': ['customer','order_status'],
    'ProducerOrder': ['order', 'producer', 'order_status', 'delivery_date'],
}
BRFN_LAT,BRFN_LON=(51.503269,-2.602925)

def create_draft_entry(request, headers, selected_model: Type[models.Model], cached_update_attempt=None, readonly_fields=None) -> dict[str, Any]:
    """
    Generates the default data for a blank "Draft" row with default values.
    Sets id to "draft" to signal creation of new entry on update.

    This allows for modification of the entry before submission to DB, 
    bypassing the need for extensive default value handling.
    """
    # Convert none to {}
    # cached_update_attempt = cached_update_attempt or {}
    draft_cells = []

    # Define default values for each field type
    default_values = {
        models.IntegerField: 0,
        models.DecimalField: 0.00,
        models.FloatField: 0.0,
        models.BooleanField: False,
        models.DateTimeField: timezone.now(),
        models.DateField: timezone.now().date(),
        models.CharField: "",
        models.TextField: "", 
        ArrayField: [],
    }

    for field_name in headers:
        draft_cell = {}
        field = selected_model._meta.get_field(field_name)

        # Use data from previous attempt or default as defined in models.py, otherwise defer to default defined above
        base_value = ""
        if field_name in cached_update_attempt:
            base_value = cached_update_attempt[field_name]
        elif field.has_default():
            base_value = field.get_default()
        else:
            for field_class, default_val in default_values.items():
                if isinstance(field, field_class):
                    base_value = default_val
                    break
        
        # Get field name, values and set appropriate flags for correct display 
        draft_cell = {
            'name': field.name,
            'value': base_value, 
            'is_fk': isinstance(field, models.ForeignKey),
            'is_bool': isinstance(field, models.BooleanField),
            'is_date': isinstance(field, (models.DateTimeField, models.DateField)),
            'is_choice': bool(getattr(field, 'choices', None)),
            'fk_options': [(str(obj.pk), str(obj)) for obj in field.related_model.objects.all()] if isinstance(field, models.ForeignKey) else [],
            'choice_options': field.choices if hasattr(field, 'choices') else [],
            'is_readonly': field_name in READONLY_FIELDS or bool(readonly_fields and field_name in readonly_fields),
            'is_password': field.name == 'password',
            'is_new': True,
        }

        # Handling for Producers who can only select their own IDs in FK fields
        if readonly_fields and field_name in readonly_fields and isinstance(field, models.ForeignKey):
            draft_cell['selected_fk_id'] = str(request.user.pk)
            draft_cell['value'] = str(request.user)
        
        draft_cells.append(draft_cell)

    # Set id to draft to flag as new entry on update
    return {'id': 'draft', 'cells': draft_cells}


def handle_management_post(request: HttpRequest, app_config: AppConfig, selected_model_name):
    """
    Handles Update and Delete POST requests for management view.
    Update - Ensure that data added is clean and fits model field constraitns.
    """
    model = app_config.get_model(selected_model_name)
    user_category = getattr(request.user, 'category', None)
    if user_category == 'Producer' and selected_model_name == "Order" and 'delete' in request.POST:
        messages.error(request, "Producers cannot delete orders.")
        return False
    print("="*50)
    print(request.POST)
    print("="*50)

    # DELETE
    if 'delete' in request.POST:
        delete_id = request.POST.get('delete')

        if delete_id == 'draft':
            # If deleting a draft  entry, simply pop the session update attempt 
            cached_update_attempt = request.session.get('cached_update_attempt', {})
            cached_update_attempt.get(selected_model_name, {}).pop('draft', None)
            request.session.modified = True
            messages.info(request, "Draft discarded.")
            return True 
        else:
            try:
                model.objects.filter(pk=delete_id).delete()
                messages.warning(request, f"Row {delete_id} deleted.")
                return True
            except Exception as e:
                print(f"FAILED TO DELETE: {e}")
                return False
    # UPDATE
    elif 'update' in request.POST:
        error_msg = None
        try:
            # Create a dynamic form class for current model
            # Exclude ID and 'password' for special handling
            exclude_fields = ['id', 'password', 'date_joined', 'last_login', 'products', 'groups', 'user_permissions']
            DynamicForm = modelform_factory(model, exclude=exclude_fields)

            #Extract unqiue row_ids and iterate through rows
            # Row ids are of format 'cell_b502c12b-...-b717b0e04c1d_<field_name>'
            # print(request.POST.keys())
            row_ids = set(key.split('_')[1] for key in request.POST.keys() if key.startswith('cell_'))
            print(f"[handle_management_post: UPDATE] FOUND {len(row_ids)} row ids.")

            # Grab data if applicable, otherwise initialise cache for update attempt
            # setdefautl here either extracts if key exists, or creates (as empty dict) if it does not.
            cached_update_attempt = request.session.setdefault('cached_update_attempt', {})
            cached_update_attempt.setdefault(selected_model_name, {})
            request.session.modified = True

            for row_id in row_ids:
                is_new_record = (row_id == 'draft') # Flag for creating new entry

                # Use record prefix to extract the field names
                # Append key/values pairs to row_data 
                row_data = {}
                prefix = f"cell_{row_id}_"
                for key, value in request.POST.items():
                    if key.startswith(prefix):
                        field_name = key.split(prefix)[1]
                        row_data[field_name] = value

                # Producer handling - force selection of own user's ID when making changes involving user FKs
                # I.e. Producer cannot create a product under another user's ID
                if user_category == 'Producer' and selected_model_name in PRODUCER_ID_FIELDS:
                    id_field = PRODUCER_ID_FIELDS[selected_model_name]
                    row_data[id_field] = str(request.user.pk)

                # print(f"\n {row_data}\n")

                if is_new_record:
                    model_instance = model()
                else:
                    model_instance = model.objects.get(pk=row_id)

                # Season fields are disabled (not submitted) when all_year is True.
                # Add the instance's current values so the form sees no change for those fields.
                if row_data.get('all_year') in ('True', 'true', '1'):
                    row_data.setdefault('seasonStart', getattr(model_instance, 'seasonStart', 'January'))
                    row_data.setdefault('seasonEnd', getattr(model_instance, 'seasonEnd', 'December'))

                # Backfill fields not submitted (e.g. disabled readonly inputs, password modal)
                # so the form sees all required fields and validates correctly.
                if not is_new_record:
                    fk_fields = {f.name for f in model._meta.get_fields() if isinstance(f, models.ForeignKey)}
                    for f in DynamicForm.base_fields:
                        if f not in row_data:
                            if f in fk_fields:
                                # Use the raw PK so the FK form field gets a valid UUID/int
                                row_data.setdefault(f, str(getattr(model_instance, f'{f}_id', '') or ''))
                            else:
                                val = getattr(model_instance, f, None)
                                if val is None:
                                    row_data.setdefault(f, '')
                                elif isinstance(val, bool):
                                    row_data.setdefault(f, str(val))
                                elif isinstance(val, list):
                                    row_data.setdefault(f, val)
                                else:
                                    row_data.setdefault(f, str(val))

                # Password-only update - bypass the form entirely to avoid interference
                password_provided = bool(selected_model_name == 'User' and row_data.get('password'))
                if password_provided:
                    password = row_data.get('password')
                    if password != row_data.get('confirm_password'):
                        error_msg = f"Passwords do not match."
                    elif not SignupForm.validate_password(password):
                        error_msg = PASSWORD_STRENGTH_ERROR
                    else:
                        #TODO DELETE DISPLAYING RAW PW
                        model_instance.set_password(password)
                        print(f"[pw_debug] set_password called, new hash prefix: {model_instance.password[:30]}")
                        model_instance.save(update_fields=['password'])
                        fresh = model_instance.__class__.objects.get(pk=model_instance.pk)
                        print(f"[pw_debug] DB hash after save: {fresh.password[:30]}, check_password: {fresh.check_password(password)}")
                        messages.success(request, f"Password updated for row {str(row_id)[:8]}.")
                        continue
                    if error_msg:
                        messages.error(request, error_msg)
                        return False

                # Apply data to model form
                form = DynamicForm(row_data, instance=model_instance)
                # Use built-in data validation
                if form.is_valid():
                    print(f"[has_changed] { {f: (form.initial.get(f), form.cleaned_data.get(f)) for f in form.changed_data} }")
                    saved_record = form.save(commit=False)
                    if error_msg:
                        messages.error(request, error_msg)
                        # Store data from update attempt to continue editing
                        _cache_attempt(request, selected_model_name, row_id, row_data)
                        return False
                    else:
                        try:
                            saved_record.save()  
                            if is_new_record:
                                messages.success(request, f"New {selected_model_name} created!")
                            else:
                                changes = ",".join(form.changed_data)
                                messages.success(request, f"Updated row {str(row_id)[:8]}: {changes}")
                            # Clear update attempt on success
                            cached_update_attempt = request.session.get('cached_update_attempt', {})
                            cached_update_attempt.pop(selected_model_name, None)
                            request.session.modified = True
                        except Exception as e:
                            messages.error(request, f"Update error: {e}")
                            return False
                else:
                    # Signal unsuccesful field updates using built-in django validation error
                    # Must format_html to render to html safely
                    error_html = format_html("<b>Error on row {}:</b><br>{}", str(row_id)[:8], form.errors)
                    messages.error(request, error_html)
                    _cache_attempt(request, selected_model_name, row_id, row_data)
                    return False
        
            return True
        
        except Exception as e:
            messages.error(request, f"Update error: {e}")
            return False
    return False

def _cache_attempt(request, selected_model_name, row_id, row_data):
    """Herlper to store data from update attempt for continued editing"""
    request.session['cached_update_attempt'][selected_model_name][str(row_id)] = row_data
    request.session.modified = True 


def get_management_context(request:HttpRequest, selected_model: Type[models.Model],
                           selected_model_name, add_new=False, row_filter=None,
                           distinct=False, readonly_fields=None, hidden_fields=['id', 'is_active', 'is_superuser'],
                           modal_id_field=None) -> dict[str, Any]:
    """
    Construct display data for selected model for management view table.
    Additionally handles row sorting logic.
    """
    PAGE_SIZE = 12
    LABEL_OVERRIDES = {
    'is_staff': 'Staff',
    'is_superuser': 'Admin',
    }
    # Construct headeres for selected mdoels
    fields = selected_model._meta.fields
    
    # Get all headers, excluding any fields in hidden_fields (defaults to hiding id).
    _hidden = hidden_fields if hidden_fields is not None else {'id'}
    visible_fields = [field for field in fields if field.name not in _hidden]
    priority = MODEL_FIELD_PRIORITY.get(selected_model_name, [])
    if priority:
        visible_fields.sort(key=lambda f: priority.index(f.name) if f.name in priority else len(priority))
    final_headers = [field.name for field in visible_fields]
    header_labels = [field.verbose_name.title() for field in visible_fields]

    header_labels = [
        LABEL_OVERRIDES.get(field.name, field.verbose_name.title())
        for field in visible_fields
    ]

    # Extract all records from model
    # Apply record filter for lower permissions if applicable (i.e., Producer)
    # Distinct due to how Orders are fetched via bridging table. Ensures that rows are unique. 
    records = selected_model.objects.filter(**row_filter) if row_filter else selected_model.objects.all()
    if distinct:
        records = records.distinct()
    print(f"[get_management_context] Found {len(records)} records")

    # Sorting logic
    # Extract direction and header to sort by
    default_sort = {
        'Order': ('order_date', 'descending'),
        'ProducerOrder': ('delivery_date', 'ascending'),
    }.get(selected_model_name, (None, 'ascending'))
    sort_field = request.GET.get('sortby', default_sort[0])
    sort_direction = request.GET.get('direction', default_sort[1])
    if sort_field:
        if sort_direction == 'descending':
            records = records.order_by(f'-{sort_field}')
        else:
            records = records.order_by(sort_field)

    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q as DQ
        search_filter = DQ()
        for field in visible_fields:
            if isinstance(field, (models.CharField, models.TextField)):
                search_filter |= DQ(**{f'{field.name}__icontains': q})
        if search_filter:
            records = records.filter(search_filter)

    paginator = Paginator(records, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    records = page_obj

    # Fetch FKs for drop-down selection fields
    foreign_key_options = {}
    for field in fields:
        if isinstance(field, models.ForeignKey):
            # Stores as list of tuples: (ID, String)
            foreign_key_options[field.name] = [(str(obj.pk), str(obj)) for obj in field.related_model.objects.all()]

    # Extract previous cached update attempt/s data for model
    cached_update_attempt = request.session.get('cached_update_attempt', {}).get(selected_model_name, {})
    
    # Populate records for display
    rows = []
    for record in records:
        # If applicable, use cell values stored from previous edit attempt in session
        # Else fallback to db
        row_id = str(record.pk)
        cached_row_update_attempt = cached_update_attempt.get(row_id, {})
        
        row_cells = []
        for field_name in final_headers:
            field = selected_model._meta.get_field(field_name)

            if field_name in cached_row_update_attempt:
                raw_val = cached_row_update_attempt[field_name]
            else:
                raw_val = getattr(record, field_name)

            display_val = format_for_display(field, raw_val)
            # Set flags for displaying cells in correct format
            cell_data = {
                'name': field.name,
                'value': display_val,
                'is_fk': isinstance(field, models.ForeignKey),
                'is_bool': isinstance(field, models.BooleanField),
                'is_date':  isinstance(field, (models.DateTimeField, models.DateField)),
                'is_choice': bool(getattr(field, 'choices', None)),
                'is_readonly': field.name in READONLY_FIELDS or bool(readonly_fields and field.name in readonly_fields),
                'is_password': field.name == 'password',
            }
            # Define drop-down options
            if cell_data['is_fk']:
                if field_name in cached_row_update_attempt:
                    cell_data['selected_fk_id'] = str(raw_val)
                else:
                    cell_data['selected_fk_id'] = str(getattr(record, f"{field.name}_id"))
                cell_data['fk_options'] = foreign_key_options[field.name]
            if cell_data['is_choice']:
                cell_data['choice_options'] = field.choices

            
            row_cells.append(cell_data)

        # For ProductBatch row, set colour class based on stock threshold status
        row_class = ''
        if selected_model_name == 'ProductBatch':
            stock = getattr(record, 'stock', None)
            threshold = getattr(record, 'stock_alert_threshold', None)
            if stock is not None and threshold is not None:
                if stock == 0:
                    row_class = 'table-danger'
                elif stock <= threshold:
                    row_class = 'table-warning'
        elif selected_model_name == 'Product':
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ]
            next_month_name = month_names[timezone.now().month % 12]
            if not getattr(record, 'all_year', True) and getattr(record, 'seasonStart', None) == next_month_name:
                row_class = 'table-info'

        modal_id = str(getattr(record, modal_id_field)) if modal_id_field else str(record.pk)
        rows.append({'id': record.pk, 'modal_id': modal_id, 'cells': row_cells, 'row_class': row_class})

    # If new row button selected, add draft row
    if add_new:
        draft_data = create_draft_entry(request, final_headers, selected_model, cached_update_attempt.get('draft', {}), readonly_fields)
        rows.insert(0, draft_data)

    return {'headers': final_headers, 'header_labels': header_labels, 'rows': rows, 'current_sort': sort_field, 'current_direction': sort_direction, 'page_obj': page_obj, 'q': q}
    
def format_for_display(field, raw_value):
    """
    Clean raw values for display.
    """
    is_date = isinstance(field, (models.DateTimeField, models.DateField))
    is_array = isinstance(raw_value, (list, tuple))
    if raw_value is None:
        return ""
    
    elif is_array:
        display_value =  ",".join(map(str, raw_value))
    
    elif is_date:
        if isinstance(raw_value, str):
            return raw_value
        return raw_value.strftime('%Y-%m-%d')

    elif field.name == 'password':
        # Skip past the fixed Argon2 params prefix to show the unique salt portion
        salt_start = raw_value.rfind('$', 0, -1) + 1  # second-to-last '$' separates params from salt
        display_value = raw_value[salt_start:salt_start + 10] + "..."
    else:
        display_value = raw_value

    return display_value
        

def get_low_stock_products(user):
    """Returns ProductBatches whose stock is at or below their per-batch alert threshold."""
    from core.models import ProductBatch
    from django.db.models import F
    qs = ProductBatch.objects.filter(stock__lte=F('stock_alert_threshold')).select_related('product')
    if not user.is_superuser:
        qs = qs.filter(product__producer=user)
    return qs

def get_pending_orders(user):
    """Returns pending ProducerOrders for the given producer/superuser."""
    from core.models import ProducerOrder
    return ProducerOrder.objects.filter(producer=user, order_status='PENDING')

def get_seasonal_coming_soon_products(user):
    """Returns a producer's products whose season begins next calendar month."""
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    next_month_name = month_names[timezone.now().month % 12]  # wraps Dec → Jan
    return Product.objects.filter(producer=user, all_year=False, seasonStart=next_month_name)
    
def get_next_occurrence(order: Order) -> date | None:
    """Calculate the next delivery date based on recurrence type."""
    today = timezone.now().date()

    if not order.recurrence_day or order.recurrence_type == 'None':
        return None


    # find the next occurrence of the chosen weekday from today
    days_ahead = (order.recurrence_day - today.isoweekday()) % 7 or 7
    next_date = today + timedelta(days=days_ahead)

    if order.recurrence_type == 'Fortnightly':
        base = order.delivery_date.date()

        # find the first recurrence_day after the original order date
        days_to_first = (order.recurrence_day - base.isoweekday()) % 7 or 7
        first_occurrence = base + timedelta(days=days_to_first)

        # advance in 7-day steps until we're on the right fortnight
        while (next_date - first_occurrence).days % 14 != 0:
            next_date += timedelta(days=7)

    # enforce 48-hour lead time - push forward if too soon
    min_date = today + timedelta(days=2)
    if next_date < min_date:
        next_date += timedelta(days=14 if order.recurrence_type == 'Fortnightly' else 7)

    return next_date

def get_recurring_orders_context(user):
    today = timezone.now().date()
    orders = Order.objects.filter(
        customer=user,
    ).exclude(recurrence_type='None').prefetch_related('orderproduct_set__batch__product__producer')

    result = []
    for order in orders:
        delivery = order.delivery_date.date()
        # Use the original delivery if it hasn't happened yet, else next recurrence
        next_date = delivery if delivery > today else get_next_occurrence(order)
        result.append({
            'order': order,
            'next_date': next_date,
            'items': order.orderproduct_set.all(),
        })
    return result

producer_distance_cache={}

def get_coordinates(postcode):
    postcode=postcode.replace(" ","")
    url=f"https://api.postcodes.io/postcodes/{postcode}"

    try:
        response=requests.get(url)
        data=response.json()

        if data["status"]==200:
            result=data["result"]
            return result["latitude"],result["longitude"]
    except Exception as e:
        print(f"Geocoding error: {e}")
    
    return None, None

def calculate_distance(lat1,lon1,lat2,lon2):
    R=3959

    lat1, lon1, lat2, lon2=map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a=(math.sin(dlat/2)**2
    + math.cos(lat1)
    * math.cos(lat2)
    * math.sin(dlon/2)**2
    )
    c=2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

User=get_user_model()

def food_mile_session_builder(user):
    session={}
    if user.postcode:
        lat,lon=get_coordinates(user.postcode)
        if lat and lon:
            session["user_coords"]={
                "lat":lat,
                "lon":lon
            }
    producers=User.objects.filter(category="Producer").values("id","postcode")
    producer_coords={}

    for p in producers:
        if not p["postcode"]:
            continue
        lat, lon = get_coordinates(p["postcode"])
        if lat and lon:
            pid=str(p["id"])
            producer_coords[pid]={
                "lat":lat,
                "lon":lon
            }
    session["producer_coords"]=producer_coords
    return session

def get_producer_food_miles(producer,customer_coords):
    key=producer.id
    if key not in producer_distance_cache:
        prod_lat, prod_lon = get_coordinates(producer.postcode)
        producer_distance_cache[key] = (prod_lat, prod_lon)

    prod_lat, prod_lon = producer_distance_cache[key]
    cus_lat, cus_lon = customer_coords

    d1 = calculate_distance(prod_lat, prod_lon, BRFN_LAT, BRFN_LON)
    d2 = calculate_distance(BRFN_LAT, BRFN_LON, cus_lat, cus_lon)

    return Decimal(d1 + d2)