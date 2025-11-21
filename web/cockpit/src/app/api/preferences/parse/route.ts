import { NextRequest, NextResponse } from 'next/server';

/**
 * POST /api/preferences/parse
 *
 * Parse natural language text into structured intent using NLP Intent Agent.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { text, account_id } = body;

    if (!text || !account_id) {
      return NextResponse.json(
        { error: 'Missing text or account_id' },
        { status: 400 }
      );
    }

    // Call Python backend API
    const backendResponse = await fetch(`http://localhost:8000/api/nlp/parse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, account_id }),
    });

    if (!backendResponse.ok) {
      const error = await backendResponse.text();
      throw new Error(`Backend error: ${error}`);
    }

    const result = await backendResponse.json();

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error parsing intent:', error);
    return NextResponse.json(
      { error: 'Failed to parse intent' },
      { status: 500 }
    );
  }
}
