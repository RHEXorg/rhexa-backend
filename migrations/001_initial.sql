-- ============================================
-- RheXa AI Business Brain - Initial Schema
-- Migration: 001_initial.sql
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PROFILES TABLE
-- ============================================
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT,
    business_name TEXT,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    weekly_report_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- DATA SOURCES TABLE
-- ============================================
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('file', 'database', 'shopify')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'error')),
    config JSONB, -- Encrypted connection details
    vector_namespace TEXT,
    file_path TEXT,
    total_chunks INTEGER DEFAULT 0,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- CHATBOTS TABLE
-- ============================================
CREATE TABLE chatbots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    data_source_ids UUID[] DEFAULT '{}',
    system_prompt TEXT,
    primary_color TEXT DEFAULT '#991b1b',
    allowed_domains TEXT[] DEFAULT '{}',
    widget_script_key TEXT UNIQUE NOT NULL DEFAULT uuid_generate_v4()::TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID REFERENCES chatbots(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'dashboard' CHECK (channel IN ('dashboard', 'widget')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- MESSAGES TABLE
-- ============================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- ALERTS TABLE
-- ============================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    data_source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- MEMORY ENTRIES TABLE
-- ============================================
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- WEEKLY REPORTS TABLE
-- ============================================
CREATE TABLE weekly_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    report_data JSONB NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE chatbots ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can only see/edit their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Data Sources: Users can only see/edit their own data sources
CREATE POLICY "Users can view own data sources" ON data_sources
    FOR SELECT USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can insert own data sources" ON data_sources
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can update own data sources" ON data_sources
    FOR UPDATE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can delete own data sources" ON data_sources
    FOR DELETE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));

-- Chatbots: Users can only see/edit their own chatbots
CREATE POLICY "Users can view own chatbots" ON chatbots
    FOR SELECT USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can insert own chatbots" ON chatbots
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can update own chatbots" ON chatbots
    FOR UPDATE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can delete own chatbots" ON chatbots
    FOR DELETE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));

-- Conversations: Users can only see/edit their own conversations
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can insert own conversations" ON conversations
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can delete own conversations" ON conversations
    FOR DELETE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));

-- Messages: Users can only see/edit messages from their conversations
CREATE POLICY "Users can view own messages" ON messages
    FOR SELECT USING (
        conversation_id IN (
            SELECT id FROM conversations 
            WHERE user_id = (SELECT id FROM profiles WHERE id = auth.uid())
        )
    );
CREATE POLICY "Users can insert own messages" ON messages
    FOR INSERT WITH CHECK (
        conversation_id IN (
            SELECT id FROM conversations 
            WHERE user_id = (SELECT id FROM profiles WHERE id = auth.uid())
        )
    );
CREATE POLICY "Users can delete own messages" ON messages
    FOR DELETE USING (
        conversation_id IN (
            SELECT id FROM conversations 
            WHERE user_id = (SELECT id FROM profiles WHERE id = auth.uid())
        )
    );

-- Alerts: Users can only see/edit their own alerts
CREATE POLICY "Users can view own alerts" ON alerts
    FOR SELECT USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can update own alerts" ON alerts
    FOR UPDATE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can insert own alerts" ON alerts
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can delete own alerts" ON alerts
    FOR DELETE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));

-- Memory Entries: Users can only see/edit their own memories
CREATE POLICY "Users can view own memories" ON memory_entries
    FOR SELECT USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can insert own memories" ON memory_entries
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can update own memories" ON memory_entries
    FOR UPDATE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can delete own memories" ON memory_entries
    FOR DELETE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));

-- Weekly Reports: Users can only see/edit their own reports
CREATE POLICY "Users can view own reports" ON weekly_reports
    FOR SELECT USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can insert own reports" ON weekly_reports
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));
CREATE POLICY "Users can delete own reports" ON weekly_reports
    FOR DELETE USING (user_id = (SELECT id FROM profiles WHERE id = auth.uid()));

-- ============================================
-- AUTO-CREATE PROFILE TRIGGER
-- ============================================
-- This trigger creates a profile automatically when a new user signs up via Supabase Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, email)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.email
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX idx_data_sources_user_id ON data_sources(user_id);
CREATE INDEX idx_data_sources_status ON data_sources(status);
CREATE INDEX idx_chatbots_user_id ON chatbots(user_id);
CREATE INDEX idx_chatbots_widget_key ON chatbots(widget_script_key);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_is_read ON alerts(is_read);
CREATE INDEX idx_memory_entries_user_id ON memory_entries(user_id);
CREATE INDEX idx_weekly_reports_user_id ON weekly_reports(user_id);
