# 🚀 SaaS Transformation Plan for Agentic RAG Platform

**Generated:** 2024-01-XX  
**Current Status:** Enterprise-ready foundation with RAG + Agent capabilities  
**Target:** Fully functional, production-ready SaaS platform

---

## 📊 Executive Summary

Your platform has an **excellent foundation** with:
- ✅ Multi-tenant architecture
- ✅ Security (JWT, FGAC, RLS)
- ✅ RAG pipeline (LlamaIndex)
- ✅ Agent orchestration (LangGraph)
- ✅ Modern UI (React + Tailwind)
- ✅ Comprehensive documentation

**To become a fully functional SaaS, you need:**
1. **Subscription & Billing System** (Stripe integration)
2. **Organization Management** (Team collaboration)
3. **Usage Tracking & Limits** (Metering & quotas)
4. **Self-Service Onboarding** (Sign-up flow)
5. **Admin Dashboard** (SaaS metrics & management)
6. **Production Infrastructure** (Deployment, monitoring, scaling)
7. **Customer Success Features** (Support, analytics, notifications)

---

## 🎯 PHASE 1: Subscription & Billing (CRITICAL - Week 1-2)

### 1.1 Stripe Integration

**Backend Implementation:**

```bash
# Install Stripe SDK
pip install stripe
```

**Create `backend/app/billing/__init__.py`:**
```python
"""Billing and subscription management"""
```

**Create `backend/app/billing/stripe_client.py`:**
```python
import stripe
from app.config import settings

stripe.api_key = settings.stripe_secret_key

class StripeClient:
    """Stripe API client wrapper"""
    
    @staticmethod
    async def create_customer(email: str, name: str, metadata: dict = None):
        """Create a Stripe customer"""
        return stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata or {}
        )
    
    @staticmethod
    async def create_subscription(customer_id: str, price_id: str):
        """Create a subscription"""
        return stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"]
        )
    
    @staticmethod
    async def cancel_subscription(subscription_id: str):
        """Cancel a subscription"""
        return stripe.Subscription.delete(subscription_id)
    
    @staticmethod
    async def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str
    ):
        """Create a Checkout session"""
        return stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url
        )
    
    @staticmethod
    async def create_portal_session(customer_id: str, return_url: str):
        """Create a billing portal session"""
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
```

**Create `backend/app/billing/plans.py`:**
```python
from enum import Enum
from typing import Dict, Any

class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class PlanLimits:
    """Plan limits and quotas"""
    
    PLANS: Dict[PlanTier, Dict[str, Any]] = {
        PlanTier.FREE: {
            "name": "Free",
            "price": 0,
            "documents": 10,
            "storage_mb": 100,
            "queries_per_month": 100,
            "users": 1,
            "api_calls_per_day": 50,
            "features": ["basic_rag", "chat_interface"]
        },
        PlanTier.STARTER: {
            "name": "Starter",
            "price": 29,
            "documents": 100,
            "storage_mb": 1000,
            "queries_per_month": 1000,
            "users": 3,
            "api_calls_per_day": 500,
            "features": ["basic_rag", "chat_interface", "document_upload", "basic_analytics"]
        },
        PlanTier.PROFESSIONAL: {
            "name": "Professional",
            "price": 99,
            "documents": 1000,
            "storage_mb": 10000,
            "queries_per_month": 10000,
            "users": 10,
            "api_calls_per_day": 5000,
            "features": [
                "advanced_rag",
                "chat_interface",
                "document_upload",
                "advanced_analytics",
                "custom_agents",
                "api_access",
                "priority_support"
            ]
        },
        PlanTier.ENTERPRISE: {
            "name": "Enterprise",
            "price": 499,
            "documents": -1,  # Unlimited
            "storage_mb": -1,  # Unlimited
            "queries_per_month": -1,  # Unlimited
            "users": -1,  # Unlimited
            "api_calls_per_day": -1,  # Unlimited
            "features": [
                "advanced_rag",
                "chat_interface",
                "document_upload",
                "advanced_analytics",
                "custom_agents",
                "api_access",
                "priority_support",
                "sso",
                "custom_integrations",
                "dedicated_support",
                "sla"
            ]
        }
    }
    
    @classmethod
    def get_plan(cls, tier: PlanTier) -> Dict[str, Any]:
        """Get plan details"""
        return cls.PLANS[tier]
    
    @classmethod
    def check_limit(cls, tier: PlanTier, resource: str, current_usage: int) -> bool:
        """Check if usage is within limits"""
        plan = cls.PLANS[tier]
        limit = plan.get(resource, 0)
        
        # -1 means unlimited
        if limit == -1:
            return True
        
        return current_usage < limit
```

**Create `backend/app/api/billing.py`:**
```python
from fastapi import APIRouter, Depends, HTTPException
from app.billing.stripe_client import StripeClient
from app.billing.plans import PlanTier, PlanLimits
from app.security.auth import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])

@router.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {
                "tier": tier.value,
                **PlanLimits.get_plan(tier)
            }
            for tier in PlanTier
        ]
    }

@router.post("/checkout")
async def create_checkout_session(
    price_id: str,
    user = Depends(get_current_user)
):
    """Create a Stripe Checkout session"""
    try:
        session = await StripeClient.create_checkout_session(
            customer_id=user.stripe_customer_id,
            price_id=price_id,
            success_url=f"{settings.frontend_url}/billing/success",
            cancel_url=f"{settings.frontend_url}/billing/cancel"
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/portal")
async def create_portal_session(user = Depends(get_current_user)):
    """Create a billing portal session"""
    try:
        session = await StripeClient.create_portal_session(
            customer_id=user.stripe_customer_id,
            return_url=f"{settings.frontend_url}/settings/billing"
        )
        return {"portal_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        
        # Handle different event types
        if event.type == "customer.subscription.created":
            # Update user subscription status
            pass
        elif event.type == "customer.subscription.updated":
            # Update subscription details
            pass
        elif event.type == "customer.subscription.deleted":
            # Handle cancellation
            pass
        elif event.type == "invoice.payment_succeeded":
            # Handle successful payment
            pass
        elif event.type == "invoice.payment_failed":
            # Handle failed payment
            pass
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Database Schema Updates:**

```sql
-- Add to Supabase migration
-- supabase/migrations/20240120000000_add_billing.sql

-- Add billing columns to organizations table
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_tier TEXT DEFAULT 'free';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_start_date TIMESTAMPTZ;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMPTZ;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ;

-- Create subscriptions table for history
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    plan_tier TEXT NOT NULL,
    status TEXT NOT NULL,
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL, -- 'documents', 'queries', 'storage', 'api_calls'
    usage_count INTEGER DEFAULT 0,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_subscriptions_org ON subscriptions(organization_id);
CREATE INDEX idx_usage_tracking_org ON usage_tracking(organization_id);
CREATE INDEX idx_usage_tracking_period ON usage_tracking(period_start, period_end);
```

**Frontend Implementation:**

```bash
# Install Stripe.js
npm install @stripe/stripe-js @stripe/react-stripe-js
```

**Create `src/pages/BillingPage.tsx`:**
```typescript
import { useState, useEffect } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import { apiClient } from '../lib/api-client'
import { CreditCard, Check } from 'lucide-react'

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY)

export const BillingPage = () => {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchPlans()
  }, [])

  const fetchPlans = async () => {
    const data = await apiClient.get('/api/billing/plans')
    setPlans(data.plans)
  }

  const handleSubscribe = async (priceId: string) => {
    setLoading(true)
    try {
      const { checkout_url } = await apiClient.post('/api/billing/checkout', {
        price_id: priceId
      })
      window.location.href = checkout_url
    } catch (error) {
      console.error('Checkout error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleManageBilling = async () => {
    try {
      const { portal_url } = await apiClient.post('/api/billing/portal')
      window.location.href = portal_url
    } catch (error) {
      console.error('Portal error:', error)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Choose Your Plan</h1>
        <p className="text-gray-600">Select the perfect plan for your needs</p>
      </div>

      <div className="grid md:grid-cols-4 gap-8">
        {plans.map((plan) => (
          <div
            key={plan.tier}
            className={`border rounded-lg p-6 ${
              plan.tier === 'professional' ? 'border-blue-500 shadow-lg' : ''
            }`}
          >
            <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
            <div className="mb-4">
              <span className="text-4xl font-bold">${plan.price}</span>
              <span className="text-gray-600">/month</span>
            </div>

            <ul className="space-y-3 mb-6">
              <li className="flex items-center">
                <Check className="w-5 h-5 text-green-500 mr-2" />
                {plan.documents === -1 ? 'Unlimited' : plan.documents} documents
              </li>
              <li className="flex items-center">
                <Check className="w-5 h-5 text-green-500 mr-2" />
                {plan.storage_mb === -1 ? 'Unlimited' : `${plan.storage_mb}MB`} storage
              </li>
              <li className="flex items-center">
                <Check className="w-5 h-5 text-green-500 mr-2" />
                {plan.queries_per_month === -1 ? 'Unlimited' : plan.queries_per_month} queries/month
              </li>
              <li className="flex items-center">
                <Check className="w-5 h-5 text-green-500 mr-2" />
                {plan.users === -1 ? 'Unlimited' : plan.users} users
              </li>
            </ul>

            <button
              onClick={() => handleSubscribe(plan.stripe_price_id)}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {plan.tier === 'free' ? 'Current Plan' : 'Subscribe'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-12 text-center">
        <button
          onClick={handleManageBilling}
          className="inline-flex items-center px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <CreditCard className="w-5 h-5 mr-2" />
          Manage Billing
        </button>
      </div>
    </div>
  )
}
```

### 1.2 Usage Tracking & Limits

**Create `backend/app/billing/usage_tracker.py`:**
```python
from datetime import datetime, timedelta
from typing import Optional
from app.billing.plans import PlanTier, PlanLimits
from supabase import create_client

class UsageTracker:
    """Track and enforce usage limits"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def track_usage(
        self,
        organization_id: str,
        resource_type: str,
        amount: int = 1
    ):
        """Track resource usage"""
        period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        # Upsert usage record
        self.supabase.table("usage_tracking").upsert({
            "organization_id": organization_id,
            "resource_type": resource_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "usage_count": amount
        }, on_conflict="organization_id,resource_type,period_start").execute()
    
    async def check_limit(
        self,
        organization_id: str,
        resource_type: str,
        plan_tier: PlanTier
    ) -> tuple[bool, int, int]:
        """Check if usage is within limits
        
        Returns: (within_limit, current_usage, limit)
        """
        # Get current usage
        period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        result = self.supabase.table("usage_tracking").select("usage_count").eq(
            "organization_id", organization_id
        ).eq("resource_type", resource_type).gte(
            "period_start", period_start.isoformat()
        ).single().execute()
        
        current_usage = result.data.get("usage_count", 0) if result.data else 0
        
        # Check against plan limits
        within_limit = PlanLimits.check_limit(plan_tier, resource_type, current_usage)
        limit = PlanLimits.get_plan(plan_tier).get(resource_type, 0)
        
        return within_limit, current_usage, limit
    
    async def get_usage_summary(self, organization_id: str) -> dict:
        """Get usage summary for organization"""
        period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        result = self.supabase.table("usage_tracking").select("*").eq(
            "organization_id", organization_id
        ).gte("period_start", period_start.isoformat()).execute()
        
        usage = {}
        for record in result.data:
            usage[record["resource_type"]] = record["usage_count"]
        
        return usage
```

**Add middleware to enforce limits:**

```python
# backend/app/middleware/usage_limiter.py
from fastapi import Request, HTTPException
from app.billing.usage_tracker import UsageTracker
from app.billing.plans import PlanTier

async def check_usage_limit(
    request: Request,
    resource_type: str,
    user
):
    """Middleware to check usage limits"""
    tracker = UsageTracker(request.app.state.supabase)
    
    within_limit, current, limit = await tracker.check_limit(
        user.organization_id,
        resource_type,
        PlanTier(user.organization.plan_tier)
    )
    
    if not within_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Usage limit exceeded. Current: {current}, Limit: {limit}. Please upgrade your plan."
        )
    
    # Track the usage
    await tracker.track_usage(user.organization_id, resource_type)
```

---

## 🎯 PHASE 2: Organization Management (Week 2-3)

### 2.1 Team Collaboration

**Database Schema:**

```sql
-- supabase/migrations/20240121000000_add_team_features.sql

-- Add team roles
CREATE TYPE team_role AS ENUM ('owner', 'admin', 'member', 'viewer');

-- Update organization_users table
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS role team_role DEFAULT 'member';
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS invited_by UUID REFERENCES users(id);
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS invited_at TIMESTAMPTZ;
ALTER TABLE organization_users ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;

-- Create team invitations table
CREATE TABLE IF NOT EXISTS team_invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role team_role DEFAULT 'member',
    invited_by UUID REFERENCES users(id),
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_team_invitations_token ON team_invitations(token);
CREATE INDEX idx_team_invitations_org ON team_invitations(organization_id);
```

**Backend API:**

```python
# backend/app/api/teams.py
from fastapi import APIRouter, Depends, HTTPException
from app.security.auth import get_current_user
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/teams", tags=["teams"])

@router.post("/invite")
async def invite_team_member(
    email: str,
    role: str,
    user = Depends(get_current_user)
):
    """Invite a team member"""
    # Check if user has permission
    if user.role not in ['owner', 'admin']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Check plan limits
    # ... usage limit check ...
    
    # Create invitation
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)
    
    invitation = supabase.table("team_invitations").insert({
        "organization_id": user.organization_id,
        "email": email,
        "role": role,
        "invited_by": user.id,
        "token": token,
        "expires_at": expires_at.isoformat()
    }).execute()
    
    # Send invitation email
    await send_invitation_email(email, token, user.organization.name)
    
    return {"message": "Invitation sent", "invitation_id": invitation.data[0]["id"]}

@router.post("/accept-invitation/{token}")
async def accept_invitation(token: str, user = Depends(get_current_user)):
    """Accept team invitation"""
    # Verify token
    invitation = supabase.table("team_invitations").select("*").eq(
        "token", token
    ).single().execute()
    
    if not invitation.data:
        raise HTTPException(status_code=404, detail="Invalid invitation")
    
    if invitation.data["expires_at"] < datetime.now().isoformat():
        raise HTTPException(status_code=400, detail="Invitation expired")
    
    # Add user to organization
    supabase.table("organization_users").insert({
        "organization_id": invitation.data["organization_id"],
        "user_id": user.id,
        "role": invitation.data["role"],
        "accepted_at": datetime.now().isoformat()
    }).execute()
    
    # Mark invitation as accepted
    supabase.table("team_invitations").update({
        "accepted_at": datetime.now().isoformat()
    }).eq("id", invitation.data["id"]).execute()
    
    return {"message": "Invitation accepted"}

@router.get("/members")
async def get_team_members(user = Depends(get_current_user)):
    """Get team members"""
    members = supabase.table("organization_users").select(
        "*, users(*)"
    ).eq("organization_id", user.organization_id).execute()
    
    return {"members": members.data}

@router.delete("/members/{user_id}")
async def remove_team_member(
    user_id: str,
    user = Depends(get_current_user)
):
    """Remove team member"""
    if user.role not in ['owner', 'admin']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    supabase.table("organization_users").delete().eq(
        "organization_id", user.organization_id
    ).eq("user_id", user_id).execute()
    
    return {"message": "Member removed"}
```

### 2.2 Organization Settings

**Create `src/pages/OrganizationSettingsPage.tsx`:**
```typescript
import { useState, useEffect } from 'react'
import { apiClient } from '../lib/api-client'
import { Users, Settings, CreditCard, Shield } from 'lucide-react'

export const OrganizationSettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general')
  const [organization, setOrganization] = useState(null)
  const [members, setMembers] = useState([])

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'members', label: 'Team Members', icon: Users },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'security', label: 'Security', icon: Shield },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Organization Settings</h1>

      <div className="flex gap-8">
        {/* Sidebar */}
        <div className="w-64">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center px-4 py-2 rounded-lg ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <tab.icon className="w-5 h-5 mr-3" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'general' && <GeneralSettings />}
          {activeTab === 'members' && <TeamMembers />}
          {activeTab === 'billing' && <BillingSettings />}
          {activeTab === 'security' && <SecuritySettings />}
        </div>
      </div>
    </div>
  )
}
```

---

## 🎯 PHASE 3: Self-Service Onboarding (Week 3)

### 3.1 Sign-Up Flow with Trial

**Update `src/pages/AuthPage.tsx`:**
```typescript
const handleSignUp = async (email: string, password: string, organizationName: string) => {
  // 1. Create user account
  const { data: authData, error: authError } = await supabase.auth.signUp({
    email,
    password,
  })

  if (authError) throw authError

  // 2. Create organization with free trial
  const { data: org } = await apiClient.post('/api/organizations', {
    name: organizationName,
    plan_tier: 'free',
    trial_ends_at: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000) // 14 days
  })

  // 3. Create Stripe customer
  await apiClient.post('/api/billing/create-customer', {
    email,
    organization_id: org.id
  })

  // 4. Send welcome email
  await apiClient.post('/api/emails/welcome', {
    email,
    organization_name: organizationName
  })

  // 5. Redirect to onboarding
  navigate('/onboarding')
}
```

### 3.2 Interactive Onboarding

**Create `src/pages/OnboardingPage.tsx`:**
```typescript
export const OnboardingPage = () => {
  const [step, setStep] = useState(1)
  const steps = [
    { id: 1, title: 'Upload Your First Document', component: <UploadStep /> },
    { id: 2, title: 'Ask Your First Question', component: <ChatStep /> },
    { id: 3, title: 'Invite Your Team', component: <InviteStep /> },
    { id: 4, title: 'Customize Settings', component: <SettingsStep /> },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex justify-between mb-2">
          {steps.map((s) => (
            <div
              key={s.id}
              className={`flex-1 h-2 rounded ${
                s.id <= step ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>
        <p className="text-center text-gray-600">
          Step {step} of {steps.length}
        </p>
      </div>

      {/* Current step */}
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h2 className="text-2xl font-bold mb-6">{steps[step - 1].title}</h2>
        {steps[step - 1].component}
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={() => setStep(Math.max(1, step - 1))}
          disabled={step === 1}
          className="px-6 py-2 border rounded disabled:opacity-50"
        >
          Previous
        </button>
        <button
          onClick={() => setStep(Math.min(steps.length, step + 1))}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {step === steps.length ? 'Finish' : 'Next'}
        </button>
      </div>
    </div>
  )
}
```

---

## 🎯 PHASE 4: Admin Dashboard (Week 4)

### 4.1 SaaS Metrics Dashboard

**Create `src/pages/AdminDashboardPage.tsx`:**
```typescript
import { useState, useEffect } from 'react'
import { apiClient } from '../lib/api-client'
import { Users, DollarSign, FileText, TrendingUp } from 'lucide-react'

export const AdminDashboardPage = () => {
  const [metrics, setMetrics] = useState({
    totalUsers: 0,
    activeSubscriptions: 0,
    mrr: 0,
    totalDocuments: 0,
    queriesThisMonth: 0,
    churnRate: 0,
  })

  useEffect(() => {
    fetchMetrics()
  }, [])

  const fetchMetrics = async ()
