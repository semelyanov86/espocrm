<?php

declare(strict_types=1);

namespace Espo\Modules\Itvolga\Tools\Telephony\Core\Ami;

/**
 * Sorts the messages of one AMI session: the response of an awaited action, the items of an awaited list action
 * (CoreShowChannels) and everything else — events above all — in arrival order. A TCP read may carry a response and
 * the events after it at once: every message of a batch is kept, none is dropped when the awaited one arrives.
 */
final class Inbox
{
    /** @var list<Message> */
    private array $queue = [];
    /** @var array<string, ?Message> */
    private array $responses = [];
    /** @var array<string, array{item: string, complete: string, accepted: bool, done: bool, denied: bool, items: list<Message>}> */
    private array $lists = [];

    public function expectResponse(string $actionId): void
    {
        $this->responses[$actionId] = null;
    }

    public function expectList(string $actionId, string $itemEvent, string $completeEvent): void
    {
        $this->lists[$actionId] = ['item' => $itemEvent, 'complete' => $completeEvent, 'accepted' => false,
            'done' => false, 'denied' => false, 'items' => []];
    }

    public function push(Message $message): void
    {
        $id = $message->actionId();

        if ($id !== null && array_key_exists($id, $this->responses) && $this->responses[$id] === null
            && $message->response() !== null) {
            $this->responses[$id] = $message;

            return;
        }

        if ($id !== null && isset($this->lists[$id]) && !$this->lists[$id]['done']) {
            $list = &$this->lists[$id];

            if ($message->response() !== null) {
                $list['accepted'] = strcasecmp($message->response(), 'Success') === 0;
                $list['denied'] = !$list['accepted'];
                $list['done'] = $list['denied'];
            } elseif ($message->event() === $list['item']) {
                $list['items'][] = $message;
            } elseif ($message->event() === $list['complete']) {
                $list['done'] = true;
            }

            unset($list);

            return;
        }

        $this->queue[] = $message;
    }

    /**
     * The awaited response once it arrived (and forgets the action).
     */
    public function takeResponse(string $actionId): ?Message
    {
        $message = $this->responses[$actionId] ?? null;

        if ($message !== null) {
            unset($this->responses[$actionId]);
        }

        return $message;
    }

    /**
     * The items of an awaited list once it is complete, false when the action was refused, null while incomplete.
     *
     * @return list<Message>|false|null
     */
    public function takeList(string $actionId): array|false|null
    {
        $list = $this->lists[$actionId] ?? null;

        if ($list === null || !$list['done']) {
            return null;
        }

        unset($this->lists[$actionId]);

        return $list['denied'] ? false : $list['items'];
    }

    /**
     * Everything that is not an awaited answer, in arrival order (and empties the queue).
     *
     * @return list<Message>
     */
    public function drain(): array
    {
        $out = $this->queue;
        $this->queue = [];

        return $out;
    }
}
