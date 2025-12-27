"""
Timeline Service
================

Timeline node yönetim servisi.
"""

import logging
from typing import List, Dict, Optional
from django.utils import timezone

from backend.courses.models import CourseContent
from backend.player.models import PlaybackSession
from ..models import TimelineNode, TimelineNodeInteraction

logger = logging.getLogger(__name__)


class TimelineService:
    """
    Timeline yönetim servisi.
    
    Sorumluluklar:
    - Node'ları getirme
    - Etkileşim kaydetme
    - Checkpoint/poll doğrulama
    """
    
    @classmethod
    def get_timeline_nodes(
        cls,
        content: CourseContent,
        include_inactive: bool = False,
    ) -> List[TimelineNode]:
        """
        İçerik için timeline node'larını getir.
        
        Args:
            content: İçerik
            include_inactive: Pasif node'ları dahil et
        
        Returns:
            TimelineNode listesi
        """
        queryset = TimelineNode.objects.filter(
            content=content,
        ).order_by('start_ts', 'order')
        
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        return list(queryset)
    
    @classmethod
    def get_chapters(cls, content: CourseContent) -> List[Dict]:
        """
        İçerik için chapter node'larını getir.
        
        Timeline navigasyonu için kullanılır.
        """
        chapters = TimelineNode.objects.filter(
            content=content,
            node_type=TimelineNode.NodeType.CHAPTER,
            is_active=True,
        ).order_by('start_ts').values('id', 'start_ts', 'title', 'config')
        
        return [
            {
                'id': str(ch['id']),
                'start_ts': ch['start_ts'],
                'title': ch['title'] or ch['config'].get('label', f"Chapter {i+1}"),
            }
            for i, ch in enumerate(chapters)
        ]
    
    @classmethod
    def record_interaction(
        cls,
        user,
        node: TimelineNode,
        interaction_type: str,
        session: PlaybackSession = None,
        video_ts: int = None,
        data: Dict = None,
    ) -> TimelineNodeInteraction:
        """
        Node etkileşimini kaydet.
        
        Args:
            user: Kullanıcı
            node: Timeline node
            interaction_type: Etkileşim türü
            session: Playback session (opsiyonel)
            video_ts: Video zamanı
            data: Ek veri (poll cevabı vs.)
        
        Returns:
            TimelineNodeInteraction
        """
        interaction = TimelineNodeInteraction.objects.create(
            tenant=user.tenant,
            node=node,
            user=user,
            session=session,
            interaction_type=interaction_type,
            video_ts=video_ts,
            data=data or {},
        )
        
        logger.info(
            f"Timeline interaction: user={user.id}, node={node.id}, "
            f"type={interaction_type}"
        )
        
        return interaction
    
    @classmethod
    def confirm_checkpoint(
        cls,
        user,
        node: TimelineNode,
        session: PlaybackSession = None,
        video_ts: int = None,
    ) -> TimelineNodeInteraction:
        """
        Checkpoint'i onayla.
        
        Args:
            user: Kullanıcı
            node: Checkpoint node
            session: Playback session
            video_ts: Video zamanı
        
        Returns:
            TimelineNodeInteraction
        """
        if node.node_type != TimelineNode.NodeType.CHECKPOINT:
            raise ValueError("Node is not a checkpoint")
        
        return cls.record_interaction(
            user=user,
            node=node,
            interaction_type=TimelineNodeInteraction.InteractionType.COMPLETED,
            session=session,
            video_ts=video_ts,
        )
    
    @classmethod
    def answer_poll(
        cls,
        user,
        node: TimelineNode,
        answer: str,
        session: PlaybackSession = None,
        video_ts: int = None,
    ) -> TimelineNodeInteraction:
        """
        Poll'u cevapla.
        
        Args:
            user: Kullanıcı
            node: Poll node
            answer: Cevap
            session: Playback session
            video_ts: Video zamanı
        
        Returns:
            TimelineNodeInteraction
        """
        if node.node_type != TimelineNode.NodeType.POLL:
            raise ValueError("Node is not a poll")
        
        return cls.record_interaction(
            user=user,
            node=node,
            interaction_type=TimelineNodeInteraction.InteractionType.ANSWERED,
            session=session,
            video_ts=video_ts,
            data={'answer': answer},
        )
    
    @classmethod
    def get_user_interactions(
        cls,
        user,
        content: CourseContent,
    ) -> Dict[str, Dict]:
        """
        Kullanıcının içerik için tüm etkileşimlerini getir.
        
        Returns:
            {node_id: {interaction_type, data, ...}}
        """
        interactions = TimelineNodeInteraction.objects.filter(
            user=user,
            node__content=content,
        ).select_related('node').order_by('-created_at')
        
        result = {}
        for interaction in interactions:
            node_id = str(interaction.node.id)
            if node_id not in result:
                result[node_id] = {
                    'interaction_type': interaction.interaction_type,
                    'data': interaction.data,
                    'created_at': interaction.created_at,
                }
        
        return result
    
    @classmethod
    def check_required_nodes_completed(
        cls,
        user,
        content: CourseContent,
    ) -> tuple:
        """
        Zorunlu node'ların tamamlanıp tamamlanmadığını kontrol et.
        
        Returns:
            (all_completed: bool, missing_nodes: List[TimelineNode])
        """
        required_nodes = TimelineNode.objects.filter(
            content=content,
            is_required=True,
            is_active=True,
        )
        
        completed_node_ids = set(
            TimelineNodeInteraction.objects.filter(
                user=user,
                node__content=content,
                interaction_type=TimelineNodeInteraction.InteractionType.COMPLETED,
            ).values_list('node_id', flat=True)
        )
        
        missing = []
        for node in required_nodes:
            if node.id not in completed_node_ids:
                missing.append(node)
        
        return len(missing) == 0, missing
    
    @classmethod
    def get_poll_results(cls, node: TimelineNode) -> Dict:
        """
        Poll sonuçlarını getir (agregat).
        
        Returns:
            {option: count, ...}
        """
        if node.node_type != TimelineNode.NodeType.POLL:
            raise ValueError("Node is not a poll")
        
        interactions = TimelineNodeInteraction.objects.filter(
            node=node,
            interaction_type=TimelineNodeInteraction.InteractionType.ANSWERED,
        )
        
        results = {}
        options = node.config.get('options', [])
        for opt in options:
            results[opt] = 0
        
        for interaction in interactions:
            answer = interaction.data.get('answer')
            if answer in results:
                results[answer] += 1
        
        total = sum(results.values())
        
        return {
            'total_responses': total,
            'results': results,
            'percentages': {
                k: round(v / total * 100, 1) if total > 0 else 0
                for k, v in results.items()
            },
        }

