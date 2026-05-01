-- Live Feed incremental setup (run after the old script)
-- This file only contains new changes you still need to execute.

-- 1) Add announcement publish time column (if not exists)
ALTER TABLE public.announcements
  ADD COLUMN IF NOT EXISTS published_at timestamptz;

-- 2) Add index for publish-time-first ordering
CREATE INDEX IF NOT EXISTS idx_announcements_category_published
  ON public.announcements (category_id, published_at DESC);

-- 3) Replace RPC: prioritize published_at, fallback to created_at
DROP FUNCTION IF EXISTS public.get_user_feed(uuid, integer, integer, integer, integer);

CREATE OR REPLACE FUNCTION public.get_user_feed(
  p_user_id uuid,
  p_per_cat_limit integer DEFAULT 10,
  p_overall_limit integer DEFAULT 50,
  p_days integer DEFAULT 90,
  p_offset integer DEFAULT 0
)
RETURNS TABLE (
  id bigint,
  title text,
  url text,
  source text,
  category_id text,
  trigger_type text,
  published_at timestamptz,
  created_at timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
WITH req AS (
  SELECT auth.uid() AS uid
),
subs AS (
  SELECT DISTINCT us.category_id
  FROM req
  JOIN public.user_subscriptions us ON us.user_id = req.uid
  WHERE req.uid IS NOT NULL
    AND req.uid = p_user_id
),
per_cat AS (
  SELECT a.id, a.title, a.url, a.source, a.category_id, a.trigger_type, a.published_at, a.created_at
  FROM subs
  CROSS JOIN LATERAL (
    SELECT id, title, url, source, category_id, trigger_type, published_at, created_at
    FROM public.announcements a
    WHERE a.category_id = subs.category_id
      AND a.category_id IS NOT NULL
      AND COALESCE(a.published_at, a.created_at) >= NOW() - (p_days || ' days')::interval
    ORDER BY COALESCE(a.published_at, a.created_at) DESC
    LIMIT p_per_cat_limit
  ) a
)
SELECT pc.id, pc.title, pc.url, pc.source, pc.category_id, pc.trigger_type, pc.published_at, pc.created_at
FROM per_cat pc
ORDER BY COALESCE(pc.published_at, pc.created_at) DESC, pc.id DESC
LIMIT p_overall_limit
OFFSET GREATEST(p_offset, 0);
$$;

GRANT EXECUTE ON FUNCTION public.get_user_feed(uuid, integer, integer, integer, integer) TO authenticated;

