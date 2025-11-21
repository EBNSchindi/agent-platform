import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/preferences/rules
 *
 * Get all user preference rules for an account.
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const account_id = searchParams.get('account_id');

    if (!account_id) {
      return NextResponse.json(
        { error: 'Missing account_id parameter' },
        { status: 400 }
      );
    }

    // Call Python backend API
    const backendResponse = await fetch(
      `http://localhost:8000/api/preferences/rules?account_id=${account_id}`
    );

    if (!backendResponse.ok) {
      const error = await backendResponse.text();
      throw new Error(`Backend error: ${error}`);
    }

    const result = await backendResponse.json();

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching rules:', error);
    return NextResponse.json(
      { error: 'Failed to fetch rules' },
      { status: 500 }
    );
  }
}
