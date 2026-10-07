"""ANSWER's additive read-only projection for method-first Cognitive POV."""
from video_contracts import read, write, now
from video_contracts.method_application import export_application


class FrozenMethodApplicationExporter:
    def export(self, bundle, status, annotation, generated_at=None):
        return export_application(bundle, status, annotation, generated_at or now())

    def export_request(self, request):
        return self.export(read(request['bundle']), read(request['status']),
                           read(request['annotation']))


def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Pure frozen method application export')
    parser.add_argument('request')
    args = parser.parse_args(); request = read(args.request)
    result = FrozenMethodApplicationExporter().export_request(request)
    if Path(request['output']).exists():
        raise ValueError('Preserve historical method application exports')
    write(request['output'], result)
    print('Frozen method application exported; no analysis or Review creation')


if __name__ == '__main__':
    main()
