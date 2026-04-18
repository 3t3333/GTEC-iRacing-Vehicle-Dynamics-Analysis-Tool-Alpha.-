-- ========================================================================================
-- OpenDAV V1.0: SimGit Enterprise Cloud Setup Script
-- Paste this entire script into your Supabase SQL Editor and click RUN.
-- This will automatically build your private telemetry database, set up zero-trust security,
-- and provision your S3 Storage bucket for team synchronization.
-- ========================================================================================

-- 1. Create the Team Members Table (Role-Based Access Control)
CREATE TABLE IF NOT EXISTS public.team_members (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Enable Row Level Security on the new table
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;

-- 2. Security Policies for team_members
-- Admins can read and update everything.
CREATE POLICY "Admins can do everything" ON public.team_members
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.team_members tm 
            WHERE tm.id = auth.uid() AND tm.role = 'admin'
        )
    );

-- Approved users can only read the team list (to see who is on the team).
CREATE POLICY "Approved users can read team" ON public.team_members
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.team_members tm 
            WHERE tm.id = auth.uid() AND tm.role IN ('admin', 'approved')
        )
    );

-- Users can always read their OWN row (to check if they are still pending).
CREATE POLICY "Users can read own row" ON public.team_members
    FOR SELECT TO authenticated
    USING (id = auth.uid());


-- 3. Auto-Admin Trigger (The first person to sign up owns the server)
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
DECLARE
    user_count INT;
BEGIN
    -- Count how many users currently exist in the team_members table
    SELECT COUNT(*) INTO user_count FROM public.team_members;
    
    -- If this is the very first user, make them the 'admin'. Otherwise, they are 'pending'.
    IF user_count = 0 THEN
        INSERT INTO public.team_members (id, email, role)
        VALUES (new.id, new.email, 'admin');
    ELSE
        INSERT INTO public.team_members (id, email, role)
        VALUES (new.id, new.email, 'pending');
    END IF;
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Bind the trigger to Supabase Auth so it fires automatically when someone registers
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();


-- 4. Provision the S3 Storage Bucket (Where the .ibt and .sto files live)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('opendav_assets', 'opendav_assets', false)
ON CONFLICT (id) DO NOTHING;


-- 5. Lock Down the Storage Bucket (Zero-Trust Security)
-- Drop any existing permissive policies we made during beta testing
DROP POLICY IF EXISTS "Allow All Authed" ON storage.objects;
DROP POLICY IF EXISTS "Give users access to own folder" ON storage.objects;

-- Create the Enterprise Security Policy:
-- ONLY users who have an 'admin' or 'approved' role in the team_members table can Upload/Download telemetry.
CREATE POLICY "SimGit Enterprise Access" ON storage.objects
    FOR ALL TO authenticated
    USING (
        bucket_id = 'opendav_assets' AND 
        EXISTS (
            SELECT 1 FROM public.team_members tm 
            WHERE tm.id = auth.uid() AND tm.role IN ('admin', 'approved')
        )
    )
    WITH CHECK (
        bucket_id = 'opendav_assets' AND 
        EXISTS (
            SELECT 1 FROM public.team_members tm 
            WHERE tm.id = auth.uid() AND tm.role IN ('admin', 'approved')
        )
    );

-- Done! Your Supabase database is now a secure SimGit backend.
