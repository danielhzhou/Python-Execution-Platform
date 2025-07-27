import React, { useState } from 'react';
import { useAppStore } from '../../stores/appStore';
import { useEditorStore } from '../../stores/editorStore';
import { projectApi } from '../../lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Upload, FileText, User, Calendar } from 'lucide-react';

interface SubmissionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SubmissionDialog({ open, onOpenChange }: SubmissionDialogProps) {
  const { currentContainer, user, setError, setLoading } = useAppStore();
  const { content } = useEditorStore();
  
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!currentContainer || !title.trim()) {
      setError('Please provide a title for your submission');
      return;
    }

    setIsSubmitting(true);
    setLoading(true);

    try {
      const response = await projectApi.submit(
        currentContainer.id,
        title.trim(),
        description.trim() || undefined
      );

      if (response.success) {
        // Reset form
        setTitle('');
        setDescription('');
        onOpenChange(false);
        
        // Show success message (you could use a toast here)
        console.log('Code submitted successfully!');
      } else {
        setError(response.error || 'Failed to submit code');
      }
    } catch (error) {
      setError('Failed to submit code');
      console.error('Submission error:', error);
    } finally {
      setIsSubmitting(false);
      setLoading(false);
    }
  };

  const codePreview = content.length > 500 
    ? content.substring(0, 500) + '...' 
    : content;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Submit Code for Review
          </DialogTitle>
          <DialogDescription>
            Submit your Python code for review by instructors or peers.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Submission Details */}
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Title *
              </label>
              <Input
                placeholder="e.g., Python Data Analysis Assignment"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">
                Description (optional)
              </label>
              <textarea
                className="w-full min-h-[100px] p-3 text-sm border border-input bg-background rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                placeholder="Describe what your code does, any specific areas you'd like feedback on, or implementation notes..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          </div>

          {/* Submission Info */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Submitter
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-sm text-muted-foreground">
                  {user?.email || 'Anonymous User'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Submission Time
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-sm text-muted-foreground">
                  {new Date().toLocaleString()}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Code Preview */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Code Preview
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="bg-muted/50 rounded-md p-3 max-h-60 overflow-y-auto">
                <pre className="text-xs font-mono whitespace-pre-wrap">
                  {codePreview}
                </pre>
                {content.length > 500 && (
                  <p className="text-xs text-muted-foreground mt-2">
                    ... and {content.length - 500} more characters
                  </p>
                )}
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>Lines: {content.split('\n').length}</span>
                <span>Characters: {content.length}</span>
                <span>Size: {Math.round(content.length / 1024 * 100) / 100} KB</span>
              </div>
            </CardContent>
          </Card>

          {/* Submission Guidelines */}
          <Card className="bg-blue-50 border-blue-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-blue-800">
                Submission Guidelines
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• Ensure your code is well-commented and follows Python best practices</li>
                <li>• Include any necessary import statements and dependencies</li>
                <li>• Test your code before submission to ensure it runs without errors</li>
                <li>• Provide clear variable names and function documentation</li>
                <li>• Consider edge cases and error handling in your implementation</li>
              </ul>
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !title.trim()}
            className="gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Submit for Review
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 