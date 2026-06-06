<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Models\AiModel;
use App\Support\GeoFlow\ApiKeyCrypto;
use App\Support\GeoFlow\OpenAiRuntimeProvider;
use RuntimeException;

/** 从 AiModel 记录构建 Content Agent 运行时配置。 */
final class AiModelRuntimeBuilder
{
    public function __construct(private readonly ApiKeyCrypto $apiKeyCrypto) {}

    /**
     * @return array{id:int,name:string,provider:string,model_id:string,provider_url:string}
     */
    public function buildFromModel(AiModel $model): array
    {
        $providerUrl = OpenAiRuntimeProvider::resolveChatBaseUrl((string) ($model->api_url ?? ''));
        $apiKey = $this->apiKeyCrypto->decrypt((string) ($model->getRawOriginal('api_key') ?? ''));
        $modelId = trim((string) ($model->model_id ?? ''));

        if ($providerUrl === '' || $apiKey === '' || $modelId === '') {
            throw new RuntimeException('AI 模型配置不完整');
        }

        $driver = OpenAiRuntimeProvider::resolveChatDriver($providerUrl, $modelId);
        $scope = 'content_agent_'.(int) $model->id;
        $providerName = OpenAiRuntimeProvider::registerProvider($scope, $driver, $providerUrl, $apiKey);

        return [
            'id' => (int) $model->id,
            'name' => (string) $model->name,
            'provider' => $providerName,
            'model_id' => $modelId,
            'provider_url' => $providerUrl,
        ];
    }

    /**
     * @return array{id:int,name:string,provider:string,model_id:string,provider_url:string,api_key:string}
     */
    public function buildForExternalPayload(AiModel $model): array
    {
        $providerUrl = OpenAiRuntimeProvider::resolveChatBaseUrl((string) ($model->api_url ?? ''));
        $apiKey = $this->apiKeyCrypto->decrypt((string) ($model->getRawOriginal('api_key') ?? ''));
        $modelId = trim((string) ($model->model_id ?? ''));

        if ($providerUrl === '' || $apiKey === '' || $modelId === '') {
            throw new RuntimeException('AI 模型配置不完整');
        }

        return [
            'id' => (int) $model->id,
            'name' => (string) $model->name,
            'provider' => OpenAiRuntimeProvider::resolveChatDriver($providerUrl, $modelId),
            'model_id' => $modelId,
            'provider_url' => $providerUrl,
            'api_key' => $apiKey,
        ];
    }
}
