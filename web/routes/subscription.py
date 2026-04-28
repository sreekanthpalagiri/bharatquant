from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from web.models import db, User, Invoice
import stripe
from web.config import Config
from datetime import datetime

bp = Blueprint('subscription', __name__, url_prefix='/subscription')

stripe.api_key = Config.STRIPE_SECRET_KEY

@bp.route('/')
@login_required
def index():
    return render_template('subscription.html')

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    data = request.get_json()
    price_id = data.get('price_id')
    
    if not price_id:
        return jsonify({'error': 'Price ID is required'}), 400
    
    try:
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=Config.BASE_URL + '/subscription/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=Config.BASE_URL + '/subscription',
            metadata={'user_id': current_user.id}
        )
        
        return jsonify({'sessionId': checkout_session.id})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/success')
@login_required
def success():
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                subscription = stripe.Subscription.retrieve(session.subscription)
                
                current_user.stripe_subscription_id = subscription.id
                current_user.subscription_status = 'active'
                
                price_id = subscription['items']['data'][0]['price']['id']
                if price_id == Config.STRIPE_PRICE_STARTER:
                    current_user.subscription_plan = 'starter'
                elif price_id == Config.STRIPE_PRICE_PRO:
                    current_user.subscription_plan = 'pro'
                elif price_id == Config.STRIPE_PRICE_TEAM:
                    current_user.subscription_plan = 'team'
                
                db.session.commit()
                flash('Subscription activated successfully!', 'success')
        except Exception as e:
            flash(f'Error processing subscription: {str(e)}', 'error')
    
    return redirect(url_for('subscription.index'))

@bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    if not current_user.stripe_subscription_id:
        return jsonify({'error': 'No active subscription'}), 400
    
    try:
        stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        flash('Subscription will be cancelled at the end of the billing period', 'success')
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    if event['type'] == 'invoice.payment_succeeded':
        invoice_data = event['data']['object']
        customer_id = invoice_data['customer']
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            invoice = Invoice(
                user_id=user.id,
                invoice_number=invoice_data['number'],
                stripe_invoice_id=invoice_data['id'],
                amount=invoice_data['amount_paid'] / 100,
                currency=invoice_data['currency'].upper(),
                status='paid',
                billing_date=datetime.fromtimestamp(invoice_data['created']),
                paid_at=datetime.fromtimestamp(invoice_data['status_transitions']['paid_at']) if invoice_data['status_transitions'].get('paid_at') else None,
                invoice_url=invoice_data.get('hosted_invoice_url'),
                pdf_url=invoice_data.get('invoice_pdf')
            )
            db.session.add(invoice)
            db.session.commit()
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription_data = event['data']['object']
        customer_id = subscription_data['customer']
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.subscription_status = 'cancelled'
            user.subscription_plan = 'starter'
            user.stripe_subscription_id = None
            db.session.commit()
    
    elif event['type'] == 'customer.subscription.updated':
        subscription_data = event['data']['object']
        customer_id = subscription_data['customer']
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.subscription_status = subscription_data['status']
            db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/portal', methods=['POST'])
@login_required
def customer_portal():
    if not current_user.stripe_customer_id:
        return jsonify({'error': 'No Stripe customer found'}), 400
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=Config.BASE_URL + '/subscription',
        )
        
        return jsonify({'url': session.url})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
