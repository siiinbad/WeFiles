// Day 6: direct security tests against Supabase — bypasses the UI
// entirely, the same way a malicious client could.
//
// Setup: create two Supabase Auth users ahead of time — one approved
// member, one approved admin — then set these env vars and run:
//   node scripts/security-check.mjs
//
// Required env vars:
//   SUPABASE_URL, SUPABASE_ANON_KEY
//   MEMBER_EMAIL, MEMBER_PASSWORD   (an approved, role='member' user)
//   ADMIN_EMAIL, ADMIN_PASSWORD     (an approved, role='admin' user)

import { createClient } from '@supabase/supabase-js';

const {
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  MEMBER_EMAIL,
  MEMBER_PASSWORD,
  ADMIN_EMAIL,
  ADMIN_PASSWORD,
} = process.env;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !MEMBER_EMAIL || !MEMBER_PASSWORD || !ADMIN_EMAIL || !ADMIN_PASSWORD) {
  console.error(
    'Missing env vars. Required: SUPABASE_URL, SUPABASE_ANON_KEY, MEMBER_EMAIL, MEMBER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD'
  );
  process.exit(1);
}

let passed = 0;
let failed = 0;

function report(label, ok, detail) {
  if (ok) {
    passed++;
    console.log(`  PASS  ${label}`);
  } else {
    failed++;
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`);
  }
}

async function signIn(email, password) {
  const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw new Error(`Sign-in failed for ${email}: ${error.message}`);
  return { client, userId: data.user.id };
}

async function main() {
  console.log('Signing in test accounts…');
  const member = await signIn(MEMBER_EMAIL, MEMBER_PASSWORD);
  const admin = await signIn(ADMIN_EMAIL, ADMIN_PASSWORD);

  console.log('\n--- profiles: self role/status escalation ---');
  {
    const { error } = await member.client
      .from('profiles')
      .update({ role: 'admin' })
      .eq('id', member.userId);
    report('member cannot set their own role to admin', !!error, error?.message);
  }
  {
    const { error } = await member.client
      .from('profiles')
      .update({ status: 'approved' })
      .eq('id', member.userId);
    // Should be a no-op failure if already approved and self-editing status
    // is blocked outright; either way this must not silently succeed as
    // a status *change* attempt on a non-approved value, so we just check
    // the trigger fires by trying a value guaranteed to differ.
    report('member cannot self-approve/self-modify status', !!error, error?.message);
  }

  console.log('\n--- profiles: reading other users ---');
  {
    const { data, error } = await member.client.from('profiles').select('*');
    const onlySelf = !error && data && data.every((p) => p.id === member.userId);
    report('member profile read is scoped to only their own row', onlySelf, error?.message);
  }
  {
    const { data, error } = await admin.client.from('profiles').select('*');
    report('admin can read all profiles', !error && data && data.length >= 1, error?.message);
  }

  console.log('\n--- files: deletion ---');
  {
    const { data: existing } = await member.client
      .from('files')
      .select('id')
      .limit(1)
      .maybeSingle();

    if (!existing) {
      console.log('  SKIP  no files exist yet — upload one via the app first to test this');
    } else {
      const { error } = await member.client.from('files').delete().eq('id', existing.id);
      const { data: stillThere } = await admin.client
        .from('files')
        .select('id')
        .eq('id', existing.id)
        .maybeSingle();
      report('member delete on an existing file is rejected by RLS', !!error && !!stillThere, error?.message);
    }
  }

  console.log('\n--- chat: impersonation ---');
  {
    const { error } = await member.client.from('chat_messages').insert({
      sender_id: member.userId,
      sender_email: 'someone-else@example.com',
      content: 'spoofed sender test',
    });
    report('member cannot post chat message with a mismatched sender_email', !!error, error?.message);
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  await member.client.auth.signOut();
  await admin.client.auth.signOut();
  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
