import { useState } from 'react';
import { ChevronDown, Bot, CheckCircle, XCircle, Loader } from 'lucide-react';
import type { SubAgentMetadata } from '@/types/subagent';

interface SubAgentSectionProps {
  metadata: SubAgentMetadata;
}

export function SubAgentSection({ metadata }: SubAgentSectionProps) {
  const [isExpanded, setIsExpanded] = useState(metadata.status === 'failed');

  const statusIcon = () => {
    switch (metadata.status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'processing':
        return <Loader className="w-4 h-4 text-muted-foreground animate-spin" />;
    }
  };

  return (
    <div className="mt-3 pt-3 border-t border-border/40">
      <button
        type="button"
        className="flex items-center gap-2 w-full text-left"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <Bot className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        <span className="text-xs font-medium text-muted-foreground">Sub-Agent Analysis</span>
        <span className="text-xs text-muted-foreground/70 truncate flex-1 min-w-0">
          {metadata.task_description}
        </span>
        {statusIcon()}
        <ChevronDown
          className={`w-3 h-3 text-muted-foreground flex-shrink-0 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-1.5 pl-6">
          <p className="text-xs text-muted-foreground">
            Document: <span className="font-medium">{metadata.document_name}</span>
          </p>

          {metadata.reasoning_steps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Reasoning:</p>
              <ol className="space-y-1 max-h-40 overflow-y-auto">
                {metadata.reasoning_steps.map((step) => (
                  <li key={step.step_number} className="text-xs text-muted-foreground flex gap-1.5">
                    <span className="flex-shrink-0 font-medium">{step.step_number}.</span>
                    <span>{step.content}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {metadata.status === 'completed' && metadata.result && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-0.5">Result:</p>
              <p className="text-sm whitespace-pre-wrap">{metadata.result}</p>
            </div>
          )}

          {metadata.status === 'failed' && metadata.error && (
            <div>
              <p className="text-xs font-medium text-red-500 mb-0.5">Error:</p>
              <p className="text-xs text-red-500">{metadata.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
