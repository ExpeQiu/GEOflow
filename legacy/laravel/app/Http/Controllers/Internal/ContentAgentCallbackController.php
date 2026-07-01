<?php

namespace App\Http\Controllers\Internal;

use App\Http\Controllers\Controller;
use App\Services\GeoFlow\ContentAgent\ContentAgentCallbackHandler;
use App\Services\GeoFlow\ContentAgent\ContentAgentCallbackSigningService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use RuntimeException;
use Throwable;

class ContentAgentCallbackController extends Controller
{
    public function __invoke(
        Request $request,
        ContentAgentCallbackSigningService $signingService,
        ContentAgentCallbackHandler $handler,
    ): JsonResponse {
        $body = (string) $request->getContent();
        $timestamp = (string) $request->header('X-Content-Agent-Timestamp', '');
        $nonce = (string) $request->header('X-Content-Agent-Nonce', '');
        $signature = (string) $request->header('X-Content-Agent-Signature', '');

        if (! $signingService->verify($request->method(), $body, $timestamp, $nonce, $signature)) {
            return response()->json(['message' => 'invalid_signature'], 401);
        }

        try {
            $payload = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
            if (! is_array($payload)) {
                throw new RuntimeException('invalid_json');
            }

            $result = $handler->handle($payload);

            return response()->json(['ok' => true, 'data' => $result]);
        } catch (Throwable $exception) {
            return response()->json([
                'ok' => false,
                'message' => $exception->getMessage(),
            ], 422);
        }
    }
}
