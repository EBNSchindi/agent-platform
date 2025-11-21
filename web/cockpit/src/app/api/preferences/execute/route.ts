import { NextRequest, NextResponse } from 'next/server';

/**
 * POST /api/preferences/execute
 *
 * Execute a parsed NLP intent.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { parsed_intent, account_id, confirmed } = body;

    if (!parsed_intent || !account_id) {
      return NextResponse.json(
        { error: 'Missing parsed_intent or account_id' },
        { status: 400 }
      );
    }

    // Call Python backend API
    const backendResponse = await fetch(`http://localhost:8000/api/nlp/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ parsed_intent, account_id, confirmed: confirmed ?? true }),
    });

    if (!backendResponse.ok) {
      const error = await backendResponse.text();
      throw new Error(`Backend error: ${error}`);
    }

    const result = await backendResponse.json();

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error executing intent:', error);
    return NextResponse.json(
      { error: 'Failed to execute intent' },
      { status: 500 }
    );
  }
}
